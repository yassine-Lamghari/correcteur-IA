import json
import logging
import os
from typing import Any, Dict

import google.generativeai as genai
from json_repair import repair_json
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.models.schemas import ExamResponse

logger = logging.getLogger("autograde")

class GeminiCorrector:
    """
    A service class for integrating with Google's Gemini API to evaluate and grade student answers.
    """
    def __init__(self):
        # Configure Gemini API key from environment variable
        api_key = os.environ.get("GEMINI_API_KEY", "")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")
    
    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception),
        reraise=True,
        before_sleep=lambda retry_state: logger.warning(
            f"Retrying Gemini API call: attempt {retry_state.attempt_number} due to {retry_state.outcome.exception()}"
        )
    )
    def _call_gemini_api(self, system_prompt: str) -> str:
        """
        Calls the Gemini API with exponential backoff retries.

        Args:
            system_prompt (str): The full prompt containing instructions and the student's answer.

        Returns:
            str: The raw text response from the API.
        """
        response = self.model.generate_content(system_prompt)
        return response.text

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
            raise ValueError(f"Impossible de parser la réponse de Gemini : {e}")