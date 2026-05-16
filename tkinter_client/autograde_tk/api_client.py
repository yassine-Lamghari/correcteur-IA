from __future__ import annotations

import requests


class AutoGradeApiClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000") -> None:
        self.base_url = base_url.rstrip("/")
        self.token = None
        self.username = None

    def login(self, username: str, password: str) -> dict:
        response = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            data={"username": username, "password": password},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        self.token = data.get("access_token")
        self.username = username
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

    def batch_grade(self, correct_answers: dict, images_b64: list, rubric_id: int | None = None) -> list:
        payload = {"correct_answers": correct_answers, "submissions": images_b64}
        if rubric_id is not None:
            payload["rubric_id"] = rubric_id
        return self._post("/api/v1/batch-grade", payload)

    def translate(self, text: str, source_lang: str = "fr", target_lang: str = "en") -> dict:
        payload = {"text": text, "source_lang": source_lang, "target_lang": target_lang}
        return self._post("/api/v1/translate", payload)

    def generate_course(self, topic: str, instructions: str, source_material: str) -> dict:
        payload = {
            "topic": topic,
            "instructions": instructions,
            "source_material": source_material
        }
        return self._post("/api/v1/courses/generate", payload, timeout=300)

    def generate_exam(self, course_content: str, instructions: str, num_questions: int) -> dict:
        payload = {
            "course_content": course_content,
            "instructions": instructions,
            "num_questions": num_questions
        }
        return self._post("/api/v1/exams/generate", payload, timeout=300)

    def generate_worksheet(self, course_content: str, instructions: str, worksheet_type: str) -> dict:
        payload = {
            "course_content": course_content,
            "instructions": instructions,
            "worksheet_type": worksheet_type
        }
        return self._post("/api/v1/worksheets/generate", payload, timeout=300)

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

    def export_course_pdf(self, course: dict) -> bytes:
        response = requests.post(
            f"{self.base_url}/api/v1/courses/export-pdf",
            json=course,
            headers=self._get_headers(),
            timeout=60
        )
        response.raise_for_status()
        return response.content

    def export_worksheet_pdf(self, worksheet: dict) -> bytes:
        response = requests.post(
            f"{self.base_url}/api/v1/worksheets/export-pdf",
            json=worksheet,
            headers=self._get_headers(),
            timeout=60
        )
        response.raise_for_status()
        return response.content

    def _post(self, path: str, payload: dict, timeout: int = 60) -> dict:
        response = requests.post(
            f"{self.base_url}{path}",
            json=payload,
            headers=self._get_headers(),
            timeout=timeout
        )
        response.raise_for_status()
        return response.json()

    def _put(self, path: str, payload: dict) -> dict:
        response = requests.put(
            f"{self.base_url}{path}",
            json=payload,
            headers=self._get_headers(),
            timeout=60,
        )
        response.raise_for_status()
        return response.json()

    def _patch(self, path: str, payload: dict) -> dict:
        response = requests.patch(
            f"{self.base_url}{path}",
            json=payload,
            headers=self._get_headers(),
            timeout=60,
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
        
    def create_submission(
        self,
        student_name: str,
        score: float,
        feedback: str,
        subject_id: int,
        student_id: str | None = None,
        answers: dict | None = None,
        exam_session_id: int | None = None,
        rubric_id: int | None = None,
        ocr_confidence: float | None = None,
        image_quality: float | None = None,
        needs_review: bool | None = None,
        review_reason: str | None = None,
        raw_text: str | None = None,
    ) -> dict:
        payload = {
            "student_name": student_name,
            "score": score,
            "feedback": feedback,
            "subject_id": subject_id,
            "student_id": student_id,
            "answers": answers,
            "exam_session_id": exam_session_id,
            "rubric_id": rubric_id,
            "ocr_confidence": ocr_confidence,
            "image_quality": image_quality,
            "needs_review": needs_review,
            "review_reason": review_reason,
            "raw_text": raw_text,
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        return self._post("/api/v1/submissions/", payload)
        
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

    # --- Students ---
    def get_students(self, class_id: int) -> list:
        return self._get(f"/api/v1/students/class/{class_id}")

    def create_students_bulk(self, class_id: int, students: list[dict]) -> list:
        payload = {"class_id": class_id, "students": students}
        return self._post("/api/v1/students/bulk", payload)

    def update_student(self, student_id: int, payload: dict) -> dict:
        return self._put(f"/api/v1/students/{student_id}", payload)

    def export_students(self, class_id: int, dest_path: str) -> None:
        response = requests.get(
            f"{self.base_url}/api/v1/students/export/{class_id}",
            headers=self._get_headers(),
            timeout=60,
        )
        response.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(response.content)

    # --- Exam Sessions ---
    def get_exam_sessions(self, subject_id: int) -> list:
        return self._get(f"/api/v1/exam-sessions/subject/{subject_id}")

    def create_exam_session(self, subject_id: int, name: str, exam_date: str | None = None) -> dict:
        payload = {"subject_id": subject_id, "name": name, "exam_date": exam_date}
        return self._post("/api/v1/exam-sessions/", payload)

    # --- Rubrics ---
    def get_rubrics(self, subject_id: int) -> list:
        return self._get(f"/api/v1/rubrics/subject/{subject_id}")

    def get_rubric(self, rubric_id: int) -> dict:
        return self._get(f"/api/v1/rubrics/{rubric_id}")

    def create_rubric(self, payload: dict) -> dict:
        return self._post("/api/v1/rubrics/", payload)

    def update_rubric(self, rubric_id: int, payload: dict) -> dict:
        return self._put(f"/api/v1/rubrics/{rubric_id}", payload)

    def replace_rubric_items(self, rubric_id: int, items: list[dict]) -> dict:
        return self._put(f"/api/v1/rubrics/{rubric_id}/items", {"items": items})

    def activate_rubric(self, rubric_id: int) -> dict:
        return self._post(f"/api/v1/rubrics/{rubric_id}/activate", {})

    # --- Review Queue ---
    def get_review_queue(self, subject_id: int) -> list:
        return self._get(f"/api/v1/review-queue/subject/{subject_id}")

    def update_review_status(self, submission_id: int, payload: dict) -> dict:
        return self._patch(f"/api/v1/review-queue/{submission_id}", payload)

    # --- Regrading ---
    def regrade_submissions(self, payload: dict) -> list:
        return self._post("/api/v1/submissions/regrade", payload)

    # --- Reports ---
    def get_report_summary(self, subject_id: int) -> dict:
        return self._get(f"/api/v1/reports/subject/{subject_id}")

    def export_report_pdf(self, subject_id: int, dest_path: str) -> None:
        response = requests.get(
            f"{self.base_url}/api/v1/reports/subject/{subject_id}/pdf",
            headers=self._get_headers(),
            timeout=60,
        )
        response.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(response.content)
