from __future__ import annotations

import base64
import logging
import re
from dataclasses import dataclass
from typing import List

from gradio_client import Client
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.models.schemas import OCRResult, OCRTask

logger = logging.getLogger("autograde")

@dataclass
class GLMOCRClient:
    """Adapter layer for GLM-OCR provider using Hugging Face Space.

    Uses `prithivMLmods/GLM-OCR-Demo` via external Gradio Client.
    """

    provider: str = settings.glm_provider
    space_id: str = "prithivMLmods/GLM-OCR-Demo"

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception),
        reraise=True,
        before_sleep=lambda retry_state: logger.warning(
            f"Retrying OCR API call: attempt {retry_state.attempt_number} due to {retry_state.outcome.exception()}"
        )
    )
    def _call_gradio_client(self, task: str, b64_data: str) -> str:
        """
        Calls the Gradio client with the provided OCR task and base64 image data.

        Args:
            task (str): The specific OCR task (e.g., "Text", "Formula").
            b64_data (str): The base64-encoded image string.

        Returns:
            str: The raw extracted text from the Gradio client.
        """
        hf_token = settings.glm_hf_token if settings.glm_hf_token else None
        client = Client(self.space_id, token=hf_token)
        return client.predict(
            task=task,
            image_b64=b64_data,
            max_new_tokens_v=4096,
            gpu_timeout_v=60,
            api_name="/run_router"
        )

    def recognize(self, image_base64: str, task: OCRTask) -> OCRResult:
        """
        Processes an image string and attempts to extract answers using the OCR model.

        Args:
            image_base64 (str): The base64 string of the image.
            task (OCRTask): The enum identifying the task.

        Returns:
            OCRResult: An object containing raw text, confidence score, and extracted lines.
        """
        # Strip the base64 prefix if present, but the space might expect it.
        # Actually in Gradio spaces, usually raw base64 works.
        b64_data = self._clean_base64(image_base64)
        
        try:
            raw_text = self._call_gradio_client(task.value, b64_data)
        except Exception as e:
            logger.error(f"OCR evaluation failed completely after retries: {str(e)}", exc_info=True)
            raise

        student_id, student_name, answers = self._parse_ocr_raw_text(raw_text)
        confidence = 0.85 # Assume high base confidence for HF service
        return OCRResult(
            raw_text=raw_text, 
            confidence=confidence, 
            student_id=student_id,
            student_name=student_name,
            extracted_answers=answers
        )

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
    def _parse_ocr_raw_text(raw_text: str) -> tuple[str | None, str | None, dict[str, str]]:
        """
        Parses OCR raw text expecting a typical template.
        Identifies ID (matricule), Name, and answers in `1 A` format.

        Returns:
            Tuple: (student_id, student_name, { "question_number": "answer" })
        """
        student_id: str | None = None
        student_name: str | None = None
        answers: dict[str, str] = {}

        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

        for line in lines:
            line_upper = line.upper()
            # Try to match ID (matricule)
            if re.match(r"^(?:ID|MATRICULE|CNE|APOGEE)[\s:]*(.+)$", line_upper):
                match = re.match(r"^(?:ID|MATRICULE|CNE|APOGEE)[\s:]+(.+)$", line, flags=re.IGNORECASE)
                if match:
                    student_id = match.group(1).strip()
                continue
            
            # Try to match Name
            if re.match(r"^(?:NOM|NAME|PRENOM|ETUDIANT)[\s:]*(.+)$", line_upper):
                match = re.match(r"^(?:NOM|NAME|PRENOM|ETUDIANT)[\w\s]*[\s:]+(.+)$", line, flags=re.IGNORECASE)
                if match:
                    student_name = match.group(1).strip()
                continue

            # Match question number patterns like "1 A", "1: B", "1 - C", "1. D"
            # Captures question number and the answer part
            match_answer = re.match(r"^(\d+)[\s:\|\.\-]+(.*)$", line)
            if match_answer:
                q_num = str(int(match_answer.group(1))) # Normalize number, e.g. '01' to '1'
                ans = match_answer.group(2).strip()
                # Store answer (might be multiple chars, keep it raw, could be "A" or "True")
                answers[q_num] = ans
                continue

        # If name is not found using the labels, leave it as None (user handles it)
        return student_id, student_name, answers
