from datetime import datetime
from enum import Enum
from typing import Any, List, Optional, Dict

from pydantic import BaseModel, EmailStr, Field

class BaseSchema(BaseModel):
    """
    Base configuration for all schemas.
    Allows creating schemas from ORM instances.
    """
    class Config:
        from_attributes = True

# --- Exam Generation Schemas ---

class ExamGenerationRequest(BaseModel):
    course_content: str = Field(..., description="Le cours ou le texte d'entrée pour générer le QCM.")
    instructions: str = Field(default="", description="Consignes pour l'examen")
    num_questions: int = Field(default=10, ge=1, le=50)

class ExamQuestion(BaseModel):
    id: int
    question: str
    option_A: str
    option_B: str
    option_C: str
    option_D: str
    correct_answer: str = Field(..., description="La lettre de la bonne réponse (A, B, C ou D)")

class ExamResponse(BaseModel):
    questions: List[ExamQuestion]

class UserBase(BaseSchema):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserLogin(BaseSchema):
    username: str
    password: str

class User(UserBase):
    id: int
    role: str

class Token(BaseModel):
    access_token: str
    token_type: str

class ClassBase(BaseSchema):
    name: str = Field(..., min_length=2, max_length=50)

class ClassCreate(ClassBase):
    pass

class Class(ClassBase):
    id: int
    user_id: int

class SubjectBase(BaseSchema):
    name: str = Field(..., min_length=2, max_length=50)

class SubjectCreate(SubjectBase):
    class_id: int

class Subject(SubjectBase):
    id: int
    class_id: int

class SubmissionBase(BaseSchema):
    student_id: Optional[str] = None
    student_name: str = Field(..., min_length=2, max_length=100)
    score: Optional[float] = Field(None, ge=0)
    feedback: Optional[str] = None
    answers: Optional[Dict[str, str]] = None

class SubmissionCreate(SubmissionBase):
    subject_id: int

class Submission(SubmissionBase):
    id: int
    subject_id: int
    created_at: datetime


class QuestionType(str, Enum):
    mcq = "mcq"
    short_answer = "short_answer"
    essay = "essay"


class OCRTask(str, Enum):
    text = "Text"
    formula = "Formula"
    table = "Table"


class QuestionSpec(BaseModel):
    question_id: str
    type: QuestionType
    prompt: str
    max_points: float = Field(..., ge=0)
    expected_answer: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)


class OCRRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded string of the image")
    task: OCRTask = OCRTask.text


class OCRResult(BaseModel):
    raw_text: str
    confidence: float = Field(..., ge=0, le=1)
    student_id: Optional[str] = None
    student_name: Optional[str] = None
    extracted_answers: Dict[str, str] = Field(default_factory=dict)


class GradeRequest(BaseModel):
    question: QuestionSpec
    student_answer: str
    use_llm: bool = False


class GradeResult(BaseModel):
    awarded_points: float = Field(..., ge=0)
    confidence: float = Field(..., ge=0, le=1)
    method: str = Field(..., description="Method used for grading, e.g., 'gemini' or 'exact_match'")
    needs_human_review: bool


class FeedbackRequest(BaseModel):
    question: QuestionSpec
    student_answer: str
    grade: GradeResult


class FeedbackResponse(BaseModel):
    feedback: str


class BatchGradeRequest(BaseModel):
    correct_answers: Dict[str, str]
    submissions: List[str]


class BatchStudentResult(BaseModel):
    student_id: Optional[str] = None
    student_name: Optional[str] = None
    score: float
    answers: Dict[str, str]
    raw_text: Optional[str] = None



class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1)
    source_lang: str = Field("fr", min_length=2, max_length=5)
    target_lang: str = Field("en", min_length=2, max_length=5)
    provider: str = Field("google")

class TranslateResponse(BaseModel):
    translated_text: str
    provider: str
