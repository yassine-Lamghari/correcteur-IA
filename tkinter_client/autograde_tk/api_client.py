from __future__ import annotations

import requests


class AutoGradeApiClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000") -> None:
        self.base_url = base_url.rstrip("/")
        self.token = None

    def login(self, username: str, password: str) -> dict:
        response = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            data={"username": username, "password": password},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        self.token = data.get("access_token")
        return data

    def register(self, username: str, email: str, password: str) -> dict:
        payload = {"username": username, "email": email, "password": password}
        response = requests.post(f"{self.base_url}/api/v1/auth/register", json=payload, timeout=30)
        response.raise_for_status()
        return response.json()

    def _get_headers(self) -> dict:
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def ocr(self, image_base64: str, task: str = "Text") -> dict:
        return self._post("/api/v1/ocr", {"image_base64": image_base64, "task": task})

    def grade(self, question: dict, student_answer: str, use_llm: bool = False) -> dict:
        payload = {"question": question, "student_answer": student_answer, "use_llm": use_llm}
        return self._post("/api/v1/grade", payload)

    def feedback(self, question: dict, student_answer: str, grade: dict) -> dict:
        payload = {"question": question, "student_answer": student_answer, "grade": grade}
        return self._post("/api/v1/feedback", payload)

    def batch_grade(self, correct_answers: dict, images_b64: list) -> list:
        payload = {"correct_answers": correct_answers, "submissions": images_b64}
        return self._post("/api/v1/batch-grade", payload)

    def translate(self, text: str, source_lang: str = "fr", target_lang: str = "en") -> dict:
        payload = {"text": text, "source_lang": source_lang, "target_lang": target_lang}
        return self._post("/api/v1/translate", payload)

    def generate_exam(self, course_content: str, instructions: str, num_questions: int) -> dict:
        payload = {
            "course_content": course_content,
            "instructions": instructions,
            "num_questions": num_questions
        }
        return self._post("/api/v1/exams/generate", payload)

    def extract_text_from_pdf(self, filepath: str) -> str:
        try:
            import pypdf
        except ImportError:
            raise ImportError("The 'pypdf' library is not installed.")
        reader = pypdf.PdfReader(filepath)
        text_parts = []
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted: text_parts.append(extracted)
        return "\n".join(text_parts)

    def export_exam_pdfs(self, exam_response: dict) -> bytes:
        response = requests.post(
            f"{self.base_url}/api/v1/exams/export-pdfs",
            json=exam_response,
            headers=self._get_headers(),
            timeout=60
        )
        response.raise_for_status()
        return response.content

    def _post(self, path: str, payload: dict) -> dict:
        response = requests.post(
            f"{self.base_url}{path}",
            json=payload,
            headers=self._get_headers(),
            timeout=60
        )
        response.raise_for_status()
        return response.json()
        
    def _get(self, path: str) -> dict:
        response = requests.get(
            f"{self.base_url}{path}",
            headers=self._get_headers(),
            timeout=60
        )
        response.raise_for_status()
        return response.json()

    # --- CRUD operations ---
    def get_classes(self) -> list:
        return self._get("/api/v1/classes/me")
        
    def create_class(self, name: str) -> dict:
        return self._post("/api/v1/classes/", {"name": name})
        
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
        response = requests.get(
            f"{self.base_url}/api/v1/export/excel/{subject_id}",
            headers=self._get_headers(),
            timeout=60
        )
        response.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(response.content)
