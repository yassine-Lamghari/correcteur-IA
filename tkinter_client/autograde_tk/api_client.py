from __future__ import annotations

import requests


class AutoGradeApiClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000") -> None:
        self.base_url = base_url.rstrip("/")

    def ocr(self, image_base64: str, task: str = "Text") -> dict:
        return self._post("/api/v1/ocr", {"image_base64": image_base64, "task": task})

    def grade(self, question: dict, student_answer: str, use_llm: bool = False) -> dict:
        payload = {"question": question, "student_answer": student_answer, "use_llm": use_llm}
        return self._post("/api/v1/grade", payload)

    def feedback(self, question: dict, student_answer: str, grade: dict) -> dict:
        payload = {"question": question, "student_answer": student_answer, "grade": grade}
        return self._post("/api/v1/feedback", payload)

    def translate(self, text: str, source_lang: str = "fr", target_lang: str = "en") -> dict:
        payload = {"text": text, "source_lang": source_lang, "target_lang": target_lang}
        return self._post("/api/v1/translate", payload)

    def _post(self, path: str, payload: dict) -> dict:
        response = requests.post(f"{self.base_url}{path}", json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
        
    def _get(self, path: str) -> dict:
        response = requests.get(f"{self.base_url}{path}", timeout=60)
        response.raise_for_status()
        return response.json()

    # --- CRUD operations ---
    def get_teachers(self) -> list:
        return self._get("/api/v1/teachers/")
        
    def create_teacher(self, name: str, email: str) -> dict:
        return self._post("/api/v1/teachers/", {"name": name, "email": email})
        
    def get_classes(self, teacher_id: int) -> list:
        return self._get(f"/api/v1/classes/teacher/{teacher_id}")
        
    def create_class(self, name: str, teacher_id: int) -> dict:
        return self._post("/api/v1/classes/", {"name": name, "teacher_id": teacher_id})
        
    def get_subjects(self, class_id: int) -> list:
        return self._get(f"/api/v1/subjects/class/{class_id}")
        
    def create_subject(self, name: str, class_id: int) -> dict:
        return self._post("/api/v1/subjects/", {"name": name, "class_id": class_id})
        
    def create_submission(self, student_name: str, score: float, feedback: str, subject_id: int) -> dict:
        return self._post("/api/v1/submissions/", {
            "student_name": student_name,
            "score": score,
            "feedback": feedback,
            "subject_id": subject_id
        })
        
    def get_submissions(self, subject_id: int) -> list:
        return self._get(f"/api/v1/submissions/subject/{subject_id}")
        
    def export_excel(self, subject_id: int, dest_path: str):
        response = requests.get(f"{self.base_url}/api/v1/export/excel/{subject_id}", timeout=60)
        response.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(response.content)
