import json
import logging
import os
from typing import Any, Dict, Optional

import google.generativeai as genai
from json_repair import repair_json
from pydantic import ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.models.schemas import CourseResponse, ExamResponse, WorksheetResponse, WorksheetType

logger = logging.getLogger("autograde")

from dotenv import load_dotenv

load_dotenv()

# Limite de caractères du support PDF/texte injecté dans le prompt (évite prompts trop longs).
_MAX_SOURCE_MATERIAL_CHARS = 32_000
# Sortie JSON + Markdown : valeur par défaut élevée (troncature = JSON invalide → erreurs).
_DEFAULT_MAX_OUTPUT_TOKENS = 16_384


def _llm_provider() -> str:
    """mistral | gemini — si LLM_PROVIDER absent, Mistral dès que MISTRAL_API_KEY est défini."""
    p = (os.environ.get("LLM_PROVIDER") or "").strip().lower()
    if p in ("mistral", "gemini"):
        return p
    if (os.environ.get("MISTRAL_API_KEY") or "").strip():
        return "mistral"
    return "gemini"


class GeminiCorrector:
    """
    LLM pour correction, QCM, cours et OCR image : Google Gemini ou Mistral (API chat).
    Choix : variable LLM_PROVIDER=mistral|gemini, ou Mistral par défaut si MISTRAL_API_KEY est défini.
    """

    def __init__(self):
        self._provider = _llm_provider()
        self.model = None
        self._model_name = ""

        if self._provider == "gemini":
            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
            genai.configure(api_key=api_key)
            self._model_name = (
                os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
            )
            self.model = genai.GenerativeModel(self._model_name)
        else:
            self._model_name = (
                os.environ.get("MISTRAL_MODEL", "mistral-small-latest").strip()
                or "mistral-small-latest"
            )

    @staticmethod
    def _response_text_or_raise(response: Any) -> str:
        """Lit response.text en traduisant les cas vides (MAX_TOKENS, SAFETY, etc.) en message clair."""
        try:
            text = response.text
        except ValueError as e:
            logger.error("Gemini: pas de texte exploitable (%s)", e)
            raise ValueError(
                "La réponse de Gemini est vide ou bloquée (limite de longueur, filtre de sécurité, ou prompt trop long). "
                "Réessayez avec un sujet plus court, moins de texte PDF en source, ou augmentez GEMINI_MAX_OUTPUT_TOKENS. "
                f"Détail : {e}"
            ) from e
        if text is None or not str(text).strip():
            raise ValueError("Réponse vide de Gemini.")
        return str(text).strip()

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception),
        reraise=True,
        before_sleep=lambda retry_state: logger.warning(
            f"Retrying Gemini API call: attempt {retry_state.attempt_number} due to {retry_state.outcome.exception()}"
        ),
    )
    def _generate_content_text(self, prompt: str, generation_config: Optional[genai.GenerationConfig] = None) -> str:
        if self._provider == "mistral":
            from app.services.mistral_client import mistral_chat_text

            json_mode = False
            max_tokens = int(os.environ.get("MISTRAL_MAX_TOKENS", "8192"))
            if generation_config is not None:
                try:
                    if getattr(generation_config, "response_mime_type", None) == "application/json":
                        json_mode = True
                    mo = getattr(generation_config, "max_output_tokens", None)
                    if mo is not None:
                        max_tokens = int(mo)
                except Exception:
                    pass
            return mistral_chat_text(prompt, json_mode=json_mode, max_tokens=max_tokens)

        kwargs: Dict[str, Any] = {}
        if generation_config is not None:
            kwargs["generation_config"] = generation_config
        response = self.model.generate_content(prompt, **kwargs)
        return self._response_text_or_raise(response)

    def _call_gemini_api(self, system_prompt: str) -> str:
        """
        Calls the Gemini API with exponential backoff retries.

        Args:
            system_prompt (str): The full prompt containing instructions and the student's answer.

        Returns:
            str: The raw text response from the API.
        """
        return self._generate_content_text(system_prompt, None)

    def evaluate_answer(self, prompt: str, student_answer: str, max_points: float) -> Dict[str, Any]:
        """
        Option 2: Intelligent auto-correction without an exact answer key.
        Uses Gemini to grade the student's answer based solely on the prompt and logic.
        
        Args:
            prompt (str): Specific grading instructions or criteria.
            student_answer (str): The OCR transcribed text of the student's exam copy.
            max_points (float): The maximum possible score for the exam.

        Returns:
            Dict[str, Any]: A dictionary containing 'score', 'feedback', and 'confidence'.
        """
        system_prompt = f"""
        You are an expert teacher. I will provide you with the OCR transcription of a complete exam copy.
        This text often contains the questions AND the student's answers (choices might be indicated, for example with the symbol ■ or [x] for checked, and □ or [ ] for unchecked, or textual answers).
        
        Specific grading instructions: {prompt}
        
        Content of the student's copy (OCR text): 
        {student_answer}
        
        Global maximum possible score: {max_points}
        
        Your task is to analyze the entire document, identify each question, evaluate the relevance of the answer provided by the student, and calculate an overall score. Rely only on common sense and general academic knowledge.
        
        Return ONLY a valid JSON object strictly respecting this structure (no surrounding text):
        {{
            "score": <float>,
            "feedback": "<Point by point detailing of the student's errors and detailed justification of the final score>",
            "confidence": <float between 0 and 1, estimating the certainty of your correction on this text>
        }}
        """
        
        try:
            text_response = self._call_gemini_api(system_prompt)
            
            # Clean up markdown codeblocks if Gemini wrapped the JSON
            if text_response.startswith("```json"):
                text_response = text_response[7:-3]
            elif text_response.startswith("```"):
                text_response = text_response[3:-3]
                
            parsed = json.loads(repair_json(text_response.strip()))
            score = float(parsed.get("score", 0))
            # clamp score
            score = max(0, min(score, max_points))
            
            return {
                "score": score,
                "feedback": parsed.get("feedback", "No feedback provided."),
                "confidence": float(parsed.get("confidence", 0.8))
            }
        except Exception as e:
            logger.error(f"Gemini evaluation failed completely after retries: {str(e)}", exc_info=True)
            # Fallback in case of error
            return {
                "score": 0,
                "feedback": f"AI evaluation error: {str(e)}",
                "confidence": 0.0
            }

    def extract_answers_from_image(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> Dict[str, Any]:
        """
        Uses Gemini's multimodal capabilities to extract student answers from a scanned exam image.
        Much more reliable than Tesseract for handwritten text.

        Args:
            image_bytes (bytes): The raw image bytes.
            mime_type (str): The MIME type of the image.

        Returns:
            Dict containing 'student_id', 'student_name', 'answers', 'confidence'.
        """
        if self._provider == "gemini" and not os.environ.get("GEMINI_API_KEY") and not os.environ.get(
            "GOOGLE_API_KEY"
        ):
            logger.warning("GEMINI_API_KEY / GOOGLE_API_KEY absent, extraction image ignorée")
            return {"student_id": None, "student_name": None, "answers": {}, "confidence": 0.0}
        if self._provider == "mistral" and not (os.environ.get("MISTRAL_API_KEY") or "").strip():
            logger.warning("MISTRAL_API_KEY absent, extraction image ignorée")
            return {"student_id": None, "student_name": None, "answers": {}, "confidence": 0.0}

        prompt = """Tu es un assistant OCR spécialisé dans la lecture de feuilles de réponses d'examens QCM.

Analyse cette image de copie d'examen et extrais :
1. Le matricule/ID de l'étudiant (si visible)
2. Le nom de l'étudiant (si visible)
3. Les réponses aux questions QCM (numéro de question → lettre de réponse A/B/C/D)

Attention : les réponses peuvent être manuscrites, cochées (■, [x], X), ou écrites à côté du numéro de question.

Retourne UNIQUEMENT un objet JSON valide (pas de markdown, pas de texte avant/après) :
{
    "student_id": "string ou null",
    "student_name": "string ou null",
    "answers": {"1": "A", "2": "B", ...},
    "confidence": 0.85
}"""

        try:
            if self._provider == "mistral":
                from app.services.mistral_client import mistral_chat_vision

                text_response = mistral_chat_vision(
                    prompt, image_bytes, mime_type, json_mode=True, max_tokens=4096
                )
            else:
                image_part = {
                    "mime_type": mime_type,
                    "data": image_bytes,
                }
                response = self.model.generate_content([prompt, image_part])
                text_response = self._response_text_or_raise(response)

            # Clean markdown wrappers
            if text_response.startswith("```json"):
                text_response = text_response[7:]
            if text_response.startswith("```"):
                text_response = text_response[3:]
            if text_response.endswith("```"):
                text_response = text_response[:-3]

            parsed = json.loads(repair_json(text_response.strip()))
            answers = parsed.get("answers", {})
            # Normalize answer keys to string numbers
            normalized_answers = {}
            for k, v in answers.items():
                key = str(int(k)) if str(k).isdigit() else str(k)
                val = str(v).strip().upper()
                if val and len(val) <= 3:  # Accept "A", "AB", etc. but not long strings
                    normalized_answers[key] = val

            return {
                "student_id": parsed.get("student_id"),
                "student_name": parsed.get("student_name"),
                "answers": normalized_answers,
                "confidence": float(parsed.get("confidence", 0.8))
            }
        except Exception as e:
            logger.error(f"Extraction réponses depuis image ({self._provider}) échouée : {str(e)}", exc_info=True)
            return {"student_id": None, "student_name": None, "answers": {}, "confidence": 0.0}

    def generate_exam(self, course_content: str, instructions: str, num_questions: int) -> ExamResponse:
        """
        Uses Gemini to generate a structured MCQ exam from a given context.
        """
        system_prompt = f"""
Tu es un professeur expert chargé de créer un examen QCM (Questions à Choix Multiples) à partir du texte/cours fourni.

Consignes:
- Génère exactement {num_questions} questions.
- Chaque question doit comporter exactement 4 choix (A, B, C, D).
- Chaque question doit avoir une et une seule bonne réponse, identifiée par sa lettre majuscule (A, B, C ou D).
- La réponse doit être uniquement un JSON valide, sans bloc markdown Markdown ni texte avant ou après.

Consignes du professeur :
'''
{instructions}
'''

Contexte du cours:
'''
{course_content}
'''

Format JSON strict attendu:
{{
  "questions": [
    {{
      "id": 1,
      "question": "Texte de la question ?",
      "option_A": "Choix 1",
      "option_B": "Choix 2",
      "option_C": "Choix 3",
      "option_D": "Choix 4",
      "correct_answer": "A"
    }}
  ]
}}
"""
        response_text = self._call_gemini_api(system_prompt)
        try:
            # Parse the JSON and ensure it conforms to our model
            data = repair_json(response_text, return_objects=True)
            if not isinstance(data, dict) or "questions" not in data:
                 raise ValueError("Structure JSON invalide (clé 'questions' absente)")
            
            validated_exam = ExamResponse.model_validate(data)
            return validated_exam
        except Exception as e:
            logger.error(f"Erreur lors de la validation du modèle d'examen : {e}", exc_info=True)
            raise ValueError(f"Impossible de parser la réponse LLM : {e}")

    def generate_course(
        self, topic: str, instructions: str = "", source_material: str = ""
    ) -> CourseResponse:
        """
        Produit un cours pédagogique complet en Markdown (structure, exemples, exercices).
        """
        if self._provider == "mistral":
            if not (os.environ.get("MISTRAL_API_KEY") or "").strip():
                raise ValueError(
                    "Clé API absente : définissez MISTRAL_API_KEY dans le fichier .env du backend."
                )
        elif not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
            raise ValueError(
                "Clé API absente : définissez GEMINI_API_KEY ou GOOGLE_API_KEY dans le fichier .env du backend."
            )

        raw_src = source_material.strip()
        if len(raw_src) > _MAX_SOURCE_MATERIAL_CHARS:
            src = (
                raw_src[:_MAX_SOURCE_MATERIAL_CHARS]
                + "\n\n[… matériel source tronqué (trop long pour le contexte) …]"
            )
        else:
            src = raw_src or "(aucun support fourni — base-toi sur le sujet et tes connaissances)"

        max_out = int(os.environ.get("GEMINI_MAX_OUTPUT_TOKENS", str(_DEFAULT_MAX_OUTPUT_TOKENS)))
        max_out = max(1024, min(max_out, 65_536))

        gen_cfg = genai.GenerationConfig(
            response_mime_type="application/json",
            max_output_tokens=max_out,
        )

        system_prompt = f"""
Tu es un professeur universitaire expert. Rédige un cours COMPLET, rigoureux et pédagogique sur le sujet indiqué.

Sujet / titre du cours :
\"\"\"{topic}\"\"\"

Consignes du demandeur (niveau, durée, style, langue, etc.) :
\"\"\"{instructions or "Niveau intermédiaire, français, cours structuré pour étudiants."}\"\"\"

Matériel source optionnel (à respecter et enrichir si présent) :
\"\"\"{src}\"\"\"

Exigences de contenu et de forme :
- Rédige ENTIÈREMENT le champ content_markdown en Markdown valide.
- Structure claire : introduction, plan / table des matières, chapitres avec titres (# ## ###), conclusion et synthèse.
- Pour chaque notion importante : définition, intuition, au moins un EXEMPLE concret chiffré ou contextualisé si pertinent.
- Inclure des encadrés "Exemple", "Remarque", "Attention" quand c'est utile.
- Proposer des exercices avec corrigés détaillés en fin de section ou en annexe.
- Ton professionnel, précis, sans remplissage inutile.
- Reste dans la limite de tokens : cours dense mais pas encyclopédique si le sujet est vaste.

Réponds UNIQUEMENT par un objet JSON valide (pas de bloc markdown, pas de texte hors JSON), avec exactement ces clés :
- "title" : chaîne, titre court du cours
- "content_markdown" : chaîne, tout le cours en Markdown (retours à la ligne autorisés dans la chaîne JSON).
"""
        try:
            response_text = self._generate_content_text(system_prompt, gen_cfg)
        except Exception as e:
            logger.error("Appel LLM (cours, %s) échoué : %s", self._provider, e, exc_info=True)
            raise ValueError(
                f"Échec d'appel au LLM ({self._provider}, modèle « {self._model_name} »). "
                "Vérifiez la clé API et le quota. Pour Mistral : MISTRAL_API_KEY ; pour Gemini : GEMINI_MODEL. "
                f"Détail : {e}"
            ) from e

        if response_text.startswith("```"):
            lines = response_text.split("\n")
            if lines and lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response_text = "\n".join(lines).strip()

        try:
            data = repair_json(response_text, return_objects=True)
            if not isinstance(data, dict):
                raise ValueError("Réponse LLM : JSON racine invalide")
            if "title" not in data or "content_markdown" not in data:
                raise ValueError("JSON invalide : clés 'title' et 'content_markdown' requises")
            title = data.get("title")
            body = data.get("content_markdown")
            if not isinstance(title, str) or not isinstance(body, str):
                raise ValueError(
                    "Le JSON doit contenir title et content_markdown sous forme de chaînes de caractères."
                )
            return CourseResponse.model_validate({"title": title.strip(), "content_markdown": body.strip()})
        except ValidationError as e:
            logger.error("Validation Pydantic du cours : %s", e)
            raise ValueError(f"Structure du cours invalide après génération : {e}") from e
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Erreur validation cours (LLM {self._provider}) : {e}", exc_info=True)
            raise ValueError(f"Impossible de parser le cours généré : {e}") from e

    def generate_worksheet(
        self,
        course_content: str,
        instructions: str = "",
        worksheet_type: WorksheetType = WorksheetType.td,
    ) -> WorksheetResponse:
        """
        Génère un TD ou TP structuré (Markdown) à partir d'un support de cours.
        """
        if self._provider == "mistral":
            if not (os.environ.get("MISTRAL_API_KEY") or "").strip():
                raise ValueError(
                    "Clé API absente : définissez MISTRAL_API_KEY dans le fichier .env du backend."
                )
        elif not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
            raise ValueError(
                "Clé API absente : définissez GEMINI_API_KEY ou GOOGLE_API_KEY dans le fichier .env du backend."
            )

        raw_src = (course_content or "").strip()
        if not raw_src:
            raise ValueError("Support de cours vide. Importez un PDF ou fournissez un texte.")

        if len(raw_src) > _MAX_SOURCE_MATERIAL_CHARS:
            src = (
                raw_src[:_MAX_SOURCE_MATERIAL_CHARS]
                + "\n\n[… matériel source tronqué (trop long pour le contexte) …]"
            )
        else:
            src = raw_src

        kind_label = "TD" if worksheet_type == WorksheetType.td else "TP"
        if worksheet_type == WorksheetType.td:
            kind_instructions = """
- Produire une série d'exercices progressifs (du simple au difficile).
- Chaque exercice contient un énoncé clair et un corrigé détaillé.
- Ajouter une courte section d'objectifs au début.
"""
        else:
            kind_instructions = """
- Décrire un travail pratique (TP) avec objectifs, prérequis et matériel.
- Proposer des étapes numérotées, des questions guidées et des résultats attendus.
- Fournir un corrigé ou une solution type en fin de document.
"""

        max_out = int(os.environ.get("GEMINI_MAX_OUTPUT_TOKENS", str(_DEFAULT_MAX_OUTPUT_TOKENS)))
        max_out = max(1024, min(max_out, 65_536))

        gen_cfg = genai.GenerationConfig(
            response_mime_type="application/json",
            max_output_tokens=max_out,
        )

        system_prompt = f"""
Tu es un enseignant expert. Génère un {kind_label} (Travaux Dirigés / Travaux Pratiques) structuré et rigoureux.

Consignes spécifiques :
{kind_instructions}

Consignes du demandeur :
{instructions or "Niveau licence, langue française, contenu clair et pédagogique."}

Support de cours :
{src}

Exigences de forme :
- Réponds UNIQUEMENT par un objet JSON valide (pas de texte hors JSON).
- Le JSON contient exactement :
  - "title" : titre du document
  - "content_markdown" : contenu complet en Markdown (sections, listes, sous-titres).
"""

        try:
            response_text = self._generate_content_text(system_prompt, gen_cfg)
        except Exception as e:
            logger.error("Appel LLM (TD/TP, %s) échoué : %s", self._provider, e, exc_info=True)
            raise ValueError(
                f"Échec d'appel au LLM ({self._provider}, modèle « {self._model_name} »). "
                "Vérifiez la clé API et le quota."
                f" Détail : {e}"
            ) from e

        if response_text.startswith("```"):
            lines = response_text.split("\n")
            if lines and lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response_text = "\n".join(lines).strip()

        try:
            data = repair_json(response_text, return_objects=True)
            if not isinstance(data, dict):
                raise ValueError("Réponse LLM : JSON racine invalide")
            if "title" not in data or "content_markdown" not in data:
                raise ValueError("JSON invalide : clés 'title' et 'content_markdown' requises")
            title = data.get("title")
            body = data.get("content_markdown")
            if not isinstance(title, str) or not isinstance(body, str):
                raise ValueError(
                    "Le JSON doit contenir title et content_markdown sous forme de chaînes de caractères."
                )
            return WorksheetResponse.model_validate(
                {"title": title.strip(), "content_markdown": body.strip()}
            )
        except ValidationError as e:
            logger.error("Validation Pydantic du TD/TP : %s", e)
            raise ValueError(f"Structure du TD/TP invalide après génération : {e}") from e
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Erreur validation TD/TP (LLM {self._provider}) : {e}", exc_info=True)
            raise ValueError(f"Impossible de parser le TD/TP généré : {e}") from e