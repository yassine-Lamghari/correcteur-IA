import google.generativeai as genai
import os
import json
from json_repair import repair_json
from typing import Dict, Any

class GeminiCorrector:
    def __init__(self):
        # Configure Gemini API key from environment variable
        api_key = os.environ.get("GEMINI_API_KEY", "")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")
    
    def evaluate_answer(self, prompt: str, student_answer: str, max_points: float) -> Dict[str, Any]:
        """
        Option 2: Intelligent auto-correction without an exact answer key.
        Uses Gemini to grade the student's answer based solely on the prompt and logic.
        """
        system_prompt = f"""
        Tu es un professeur expert. Je vais te donner la retranscription OCR d'une copie d'examen complète.
        Ce texte contient souvent les questions ET les réponses de l'étudiant (les choix de réponse peuvent y être indiqués, par exemple avec le symbole ■ ou [x] pour coché, et □ ou [ ] pour non coché, ou des réponses textuelles).
        
        Consignes spécifiques pour la correction : {prompt}
        
        Contenu de la copie de l'étudiant (Texte OCR) : 
        {student_answer}
        
        Note maximale possible globale: {max_points}
        
        Ta tâche est d'analyser le document en entier, d'identifier chaque question, d'évaluer la pertinence de la réponse fournie par l'étudiant et de calculer une note globale. Ne t'appuie que sur le bon sens et les connaissances académiques générales.
        
        Renvoie UNIQUEMENT un objet JSON valide en respectant exactement cette structure (aucun texte autour):
        {{
            "score": <float>,
            "feedback": "<Détail point par point des erreurs de l'étudiant et justification détaillée de la note finale>",
            "confidence": <float entre 0 et 1, estimant la certitude de ta correction de ce texte>
        }}
        """
        
        try:
            response = self.model.generate_content(system_prompt)
            text_response = response.text
            
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
            # Fallback in case of error
            return {
                "score": 0,
                "feedback": f"Erreur lors de l'évaluation par l'IA: {str(e)}",
                "confidence": 0.0
            }