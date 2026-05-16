from __future__ import annotations

import base64
import cv2
import logging
import re
from dataclasses import dataclass
from io import BytesIO
from typing import List

import numpy as np
import pytesseract
from PIL import Image

# Indiquer le chemin absolu vers l'exécutable Tesseract sous Windows
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

from app.core.config import settings
from app.models.schemas import OCRResult, OCRTask

logger = logging.getLogger("autograde")

@dataclass
class GLMOCRClient:
    """OCR client that uses Tesseract as primary and Gemini as fallback.

    Tesseract handles printed text. When it fails to extract MCQ answers
    (common with handwritten responses), Gemini's multimodal API is used
    as a fallback to read the image directly.
    """

    provider: str = settings.glm_provider
    _gemini: object = None

    @property
    def gemini(self):
        """Lazy-load GeminiCorrector only when needed."""
        if self._gemini is None:
            from app.services.gemini import GeminiCorrector
            self._gemini = GeminiCorrector()
        return self._gemini

    def recognize(self, image_base64: str, task: OCRTask) -> OCRResult:
        """
        Processes an image string and attempts to extract answers using Tesseract OCR.

        Args:
            image_base64 (str): The base64 string of the image.
            task (OCRTask): The enum identifying the task (preserved for compatibility).

        Returns:
            OCRResult: An object containing raw text, confidence score, and extracted lines.
        """
        image_quality = None
        try:
            clean_b64 = self._clean_base64(image_base64)
            image_bytes = base64.b64decode(clean_b64)
            image = Image.open(BytesIO(image_bytes))
            image = self._auto_crop(image)
            image = self._auto_rotate(image)
            image_bytes = self._encode_image(image)
            clean_b64 = base64.b64encode(image_bytes).decode("utf-8")
            image_quality = self._estimate_image_quality(image_bytes)
            # Find extension if possible or default to jpeg
            b64_with_prefix = f"data:image/jpeg;base64,{clean_b64}"
            
            logger.info("[DEBUG] Appel de prithivMLmods/GLM-OCR-Demo sur Hugging Face Space...")
            from gradio_client import Client
            
            # Utiliser le token depuis .env (AUTOGRADE_GLM_HF_TOKEN) s'il existe
            hf_token = settings.glm_hf_token or None
            hf_client = Client("prithivMLmods/GLM-OCR-Demo", token=hf_token)
            
            raw_text = hf_client.predict(
                task="Text",
                image_b64=b64_with_prefix,
                max_new_tokens_v=4096,
                gpu_timeout_v=60,
                api_name="/run_router"
            )
            
            logger.info(f"[DEBUG] Texte brut depuis GLM-OCR: '{raw_text}', longueur: {len(raw_text) if raw_text else 0}")

            if not raw_text or raw_text.strip() == "" or "Unlogged user is running out" in raw_text:
                if raw_text and "Unlogged user is running out" in raw_text:
                    logger.error("[DEBUG] Limite de quota Hugging Face atteinte.")
                else:
                    logger.warning("[DEBUG] GLM-OCR a échoué ou retourné un texte vide. On passe au fallback Gemini.")
                raw_text = ""
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Erreur avec Hugging Face GLM-OCR Space: {error_msg}", exc_info=True)
            raw_text = ""

        student_id, student_name, answers = self._parse_ocr_raw_text(raw_text)
        logger.info(f"[DEBUG] Parsed results - ID: {student_id}, Name: {student_name}, Answers: {answers}")

        # If Tesseract extracted no answers, try Gemini as fallback
        if not answers:
            logger.warning("[DEBUG] Tesseract extracted no answers, trying Gemini fallback...")
            try:
                clean_b64_retry = self._clean_base64(image_base64)
                image_bytes_retry = base64.b64decode(clean_b64_retry)

                # Detect MIME type from image header
                img_for_mime = Image.open(BytesIO(image_bytes_retry))
                mime_map = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
                mime_type = mime_map.get(img_for_mime.format, "image/jpeg")

                gemini_result = self.gemini.extract_answers_from_image(image_bytes_retry, mime_type)
                if gemini_result.get("answers"):
                    logger.info(f"[DEBUG] Gemini fallback extracted {len(gemini_result['answers'])} answers")
                    # Use Gemini results
                    if not student_id and gemini_result.get("student_id"):
                        student_id = gemini_result["student_id"]
                    if not student_name and gemini_result.get("student_name"):
                        student_name = gemini_result["student_name"]
                    answers = gemini_result["answers"]
                    confidence = gemini_result.get("confidence", 0.8)
                    logger.info(f"[DEBUG] Gemini fallback extracted {len(answers)} answers")
                else:
                    logger.warning("[DEBUG] Gemini fallback also found no answers")
                    confidence = 0.3
            except Exception as gemini_err:
                logger.warning(f"[DEBUG] Gemini OCR fallback failed: {gemini_err}")
                confidence = 0.3
        else:
            confidence = 0.8

        # Validate that we found some answers
        if not answers:
            logger.warning("[DEBUG] No answers found in the OCR text")
            if raw_text and raw_text.strip():
                raw_text += "\n\n[AVERTISSEMENT] Aucune réponse QCM (A/B/C/D) trouvée dans l'image."
            else:
                raw_text = "[ERREUR] Le système n'a pu lire AUCUN texte depuis cette image (Tesseract et Gemini ont échoué ou retourné vide)."

        return OCRResult(
            raw_text=raw_text,
            confidence=confidence,
            student_id=student_id,
            student_name=student_name,
            extracted_answers=answers,
            image_quality=image_quality,
        )

    @staticmethod
    def _preprocess_image(image: Image.Image) -> Image.Image:
        """
        Preprocesses image for better OCR results.
        
        Args:
            image (Image.Image): The PIL Image object.
            
        Returns:
            Image.Image: The preprocessed image.
        """
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert PIL Image to numpy array
        img_array = np.array(image)
        
        # Convert to grayscale
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Just convert to grayscale and return, Tesseract handles binarization well itself
        # No thresholding as it has proven to destroy text in camera images with shadows
        return Image.fromarray(gray)

    @staticmethod
    def _clean_base64(payload: str) -> str:
        """
        Removes the data URI prefix from a base64 string if present.

        Args:
            payload (str): The potentially prefixed base64 string.

        Returns:
            str: The clean base64 string.
        """
        # Keep only the raw base64 text if data URI is present
        if "," in payload:
            return payload.split(",", 1)[1]
        return payload

    @staticmethod
    def _estimate_image_quality(image_bytes: bytes) -> float | None:
        try:
            image = Image.open(BytesIO(image_bytes)).convert("L")
            img_array = np.array(image)
            lap_var = cv2.Laplacian(img_array, cv2.CV_64F).var()
            normalized = min(lap_var / 1000.0, 1.0)
            return round(float(normalized), 3)
        except Exception:
            return None

    @staticmethod
    def _auto_rotate(image: Image.Image) -> Image.Image:
        try:
            osd = pytesseract.image_to_osd(image)
            match = re.search(r"Rotate: (\d+)", osd)
            angle = int(match.group(1)) if match else 0
            if angle:
                return image.rotate(-angle, expand=True)
        except Exception:
            pass
        return image

    @staticmethod
    def _auto_crop(image: Image.Image) -> Image.Image:
        try:
            gray = image.convert("L")
            thresh = gray.point(lambda p: 0 if p > 245 else 255, "1")
            bbox = thresh.getbbox()
            if bbox:
                return image.crop(bbox)
        except Exception:
            pass
        return image

    @staticmethod
    def _encode_image(image: Image.Image) -> bytes:
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=92)
        return buffer.getvalue()

    @staticmethod
    def _parse_ocr_raw_text(raw_text: str) -> tuple[str | None, str | None, dict[str, str]]:
        """
        Parses OCR raw text expecting a typical template.
        Identifies ID (matricule), Name, and answers in 1 A format.
Returns:
            Tuple: (student_id, student_name, { "question_number": "answer" })
        """
        student_id: str | None = None
        student_name: str | None = None
        answers: dict[str, str] = {}

        logger.info(f"[DEBUG] Raw Text from OCR (first 100 chars): {raw_text[:100]}")
        with open("last_ocr_raw.txt", "w", encoding="utf-8") as f:
            f.write(raw_text)

        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        logger.info(f"[DEBUG] Processing {len(lines)} lines from OCR")

        ocr_map = {'8': 'B', '0': 'D', '4': 'A', '1': 'I', '5': 'C', '6': 'C', '2': 'Z', '9': 'C'}
        valid_answers = {'A', 'B', 'C', 'D', 'E', 'F', 'V', 'F'} # Vrai/Faux aussi si besoin

        for line in lines:
            logger.info(f"[DEBUG] Processing line: '{line}'")
            line_upper = line.upper()
            # Try to match ID (matricule)
            if re.search(r"(?:ID|MATRICULE|CNE|APOGEE)[\s:]*(.+)$", line_upper):
                match = re.search(r"(?:ID|MATRICULE|CNE|APOGEE)[\s:]+(.+)$", line, flags=re.IGNORECASE)
                if match:
                    student_id = match.group(1).strip()
                continue
            
            # Try to match Name
            if re.search(r"(?:NOM|NAME|PRENOM|ETUDIANT)[\s:]*(.+)$", line_upper):
                match = re.search(r"(?:NOM|NAME|PRENOM|ETUDIANT)[\w\s]*[\s:]+(.+)$", line, flags=re.IGNORECASE)
                if match:
                    student_name = match.group(1).strip()
                continue

            # Match strict question answer pair, allowing common OCR number substitutions
            # Valid answers typically A, B, C, D. OCR might read them as 4(A), 8(B), 0(D), 6(C/G), 5(S), etc.
            match_answer = re.search(r"^\s*(?:\|\s*)?(?:(?:Q|Question)\s*)?(?:\*\*)?\s*(\d+)\s*(?:\*\*)?[\s:\|\.\-\)]*([A-Za-z]{1,5}|[0-9])[\s:\|\.\-\)]*(?:\*)?$", line, flags=re.IGNORECASE)

            if match_answer:
                q_num = str(int(match_answer.group(1))) # Normalize number, e.g. '01' to '1'
                ans_raw = match_answer.group(2).strip().upper()
                
                # Apply OCR corrections
                if ans_raw in ocr_map:
                    ans_raw = ocr_map[ans_raw]
                
                # S'il trouve plus d'une lettre (ex "ABCD" ou "Ceci"), le rejeter.
                # On ne garde que les lettres de taille 1 qui sont valides.
                if len(ans_raw) == 1 and ans_raw in valid_answers:
                    answers[q_num] = ans_raw
                # Special case where answer may be inside a larger string is handled by a secondary global pass below.
                continue

        # Second passe pour capturer ce qui n'a pas été lu par lignes mais qui float dans le texte
        # Ex: "1 A 2 B 3C" sur la même ligne.
        matches = re.finditer(r"(?:^|\s|Q|Question|\|)(?:\*\*)?(\d+)(?:\*\*)?[\s:\|\.\-\)]*([A-Za-z]|[0-9])(?=\s|$|\||\.)", raw_text, re.IGNORECASE)
        for m in matches:
            q_num = str(int(m.group(1))) # Normalize number to get rid of leading zeroes
            if q_num not in answers: # Only add if not already caught by line-processing 
                ans_raw = m.group(2).upper()
                if ans_raw in ocr_map:
                    ans_raw = ocr_map[ans_raw]
                if ans_raw in valid_answers:
                     answers[q_num] = ans_raw

        # If name is not found using the labels, leave it as None (user handles it)
        return student_id, student_name, answers
