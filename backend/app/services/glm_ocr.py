from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from typing import List
from gradio_client import Client

from app.core.config import settings
from app.models.schemas import OCRResult, OCRTask


@dataclass
class GLMOCRClient:
    """Adapter layer for GLM-OCR provider using Hugging Face Space.

    Uses `prithivMLmods/GLM-OCR-Demo` via external Gradio Client.
    """

    provider: str = settings.glm_provider
    space_id: str = "prithivMLmods/GLM-OCR-Demo"

    def recognize(self, image_base64: str, task: OCRTask) -> OCRResult:
        # Strip the base64 prefix if present, but the space might expect it.
        # Actually in Gradio spaces, usually raw base64 works.
        b64_data = self._clean_base64(image_base64)
        
        # Using Gradio Client to hit the HF Space
        # Passing the token if it exists in settings to avoid limits
        hf_token = settings.glm_hf_token if settings.glm_hf_token else None
        client = Client(self.space_id, token=hf_token)
        raw_text = client.predict(
            task=task.value,
            image_b64=b64_data,
            max_new_tokens_v=4096,
            gpu_timeout_v=60,
            api_name="/run_router"
        )
        
        answers = self._extract_answers(raw_text)
        confidence = 0.85 # Assume high base confidence for HF service
        return OCRResult(raw_text=raw_text, confidence=confidence, extracted_answers=answers)

    @staticmethod
    def _clean_base64(payload: str) -> str:
        # Keep only the raw base64 text if data URI is present
        if "," in payload:
            return payload.split(",", 1)[1]
        return payload

    @staticmethod
    def _extract_answers(raw_text: str) -> List[str]:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        answers: List[str] = []
        for line in lines:
            match = re.split(r"[:|]", line, maxsplit=1)
            if len(match) == 2:
                answers.append(match[1].strip())
            else:
                answers.append(line)
        return answers
