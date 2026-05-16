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


class CourseGenerationRequest(BaseModel):
    topic: str = Field(..., min_length=3, description="Sujet ou titre du cours à produire.")
    instructions: str = Field(
        default="",
        description="Niveau (ex. L1), durée souhaitée, public, style pédagogique, langue.",
    )
    source_material: str = Field(
        default="",
        description="Texte ou notes optionnelles à intégrer (extrait PDF, plan, etc.).",
    )


class CourseResponse(BaseModel):
    title: str = Field(..., description="Titre du cours")
    content_markdown: str = Field(
        ...,
        description="Cours complet en Markdown (titres, listes, exemples, encadrés).",
    )


class WorksheetType(str, Enum):
    td = "td"
    tp = "tp"


class WorksheetGenerationRequest(BaseModel):
    course_content: str = Field(..., description="Support de cours pour générer le TD/TP.")
    instructions: str = Field(default="", description="Consignes pour le TD/TP")
    worksheet_type: WorksheetType = Field(default=WorksheetType.td)


class WorksheetResponse(BaseModel):
    title: str = Field(..., description="Titre du TD/TP")
    content_markdown: str = Field(
        ...,
        description="TD/TP complet en Markdown (sections, exercices, corrigés).",
    )


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


class QuestionType(str, Enum):
    mcq = "mcq"
    short_answer = "short_answer"
    essay = "essay"


class OCRTask(str, Enum):
    text = "Text"
    formula = "Formula"
    table = "Table"


class StudentBase(BaseSchema):
    student_code: str = Field(..., min_length=2, max_length=50)
    full_name: str = Field(..., min_length=2, max_length=120)
    email: Optional[EmailStr] = None


class StudentCreate(StudentBase):
    class_id: int


class StudentUpdate(BaseSchema):
    full_name: Optional[str] = Field(None, min_length=2, max_length=120)
    email: Optional[EmailStr] = None


class Student(StudentBase):
    id: int
    class_id: int
    created_at: datetime


class BulkStudentCreate(BaseModel):
    class_id: int
    students: List[StudentBase] = Field(default_factory=list)


class ExamSessionBase(BaseSchema):
    name: str = Field(..., min_length=2, max_length=80)
    exam_date: Optional[datetime] = None


class ExamSessionCreate(ExamSessionBase):
    subject_id: int


class ExamSession(ExamSessionBase):
    id: int
    subject_id: int
    created_at: datetime


class RubricItemBase(BaseSchema):
    question_id: str = Field(..., min_length=1, max_length=30)
    question_type: QuestionType = QuestionType.mcq
    max_points: float = Field(..., ge=0)
    expected_answer: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    order_index: int = 0


class RubricItemCreate(RubricItemBase):
    pass


class RubricItem(RubricItemBase):
    id: int
    rubric_id: int


class RubricBase(BaseSchema):
    name: str = Field(..., min_length=2, max_length=120)
    description: Optional[str] = None
    total_points: Optional[float] = Field(None, ge=0)
    is_active: bool = False


class RubricCreate(RubricBase):
    subject_id: int
    items: List[RubricItemCreate] = Field(default_factory=list)


class RubricUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class RubricItemsUpdate(BaseModel):
    items: List[RubricItemCreate] = Field(default_factory=list)


class Rubric(RubricBase):
    id: int
    subject_id: int
    created_at: datetime
    items: List[RubricItem] = Field(default_factory=list)

class SubmissionBase(BaseSchema):
    student_id: Optional[str] = None
    student_name: str = Field(..., min_length=2, max_length=100)
    score: Optional[float] = Field(None, ge=0)
    feedback: Optional[str] = None
    answers: Optional[Dict[str, str]] = None

class SubmissionCreate(SubmissionBase):
    subject_id: int
    exam_session_id: Optional[int] = None
    rubric_id: Optional[int] = None
    ocr_confidence: Optional[float] = Field(None, ge=0, le=1)
    image_quality: Optional[float] = Field(None, ge=0, le=1)
    needs_review: Optional[bool] = False
    review_reason: Optional[str] = None
    raw_text: Optional[str] = None

class Submission(SubmissionBase):
    id: int
    subject_id: int
    created_at: datetime


class SubmissionMetaBase(BaseSchema):
    exam_session_id: Optional[int] = None
    ocr_confidence: Optional[float] = Field(None, ge=0, le=1)
    image_quality: Optional[float] = Field(None, ge=0, le=1)
    needs_review: Optional[bool] = False
    review_reason: Optional[str] = None
    review_status: Optional[str] = None
    raw_text: Optional[str] = None


class SubmissionMeta(SubmissionMetaBase):
    id: int
    submission_id: int
    created_at: datetime


class SubmissionGradeBase(BaseSchema):
    rubric_id: int
    score: float = Field(..., ge=0)
    max_score: float = Field(..., ge=0)
    details: Optional[Dict[str, Any]] = None
    is_current: bool = True


class SubmissionGrade(SubmissionGradeBase):
    id: int
    submission_id: int
    created_at: datetime


class RegradeRequest(BaseModel):
    rubric_id: int
    subject_id: Optional[int] = None
    submission_ids: Optional[List[int]] = None


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
    image_quality: Optional[float] = Field(None, ge=0, le=1)


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
    rubric_id: Optional[int] = None


class BatchStudentResult(BaseModel):
    student_id: Optional[str] = None
    student_name: Optional[str] = None
    score: float
    answers: Dict[str, str]
    raw_text: Optional[str] = None
    ocr_confidence: Optional[float] = None
    image_quality: Optional[float] = None
    needs_review: Optional[bool] = None
    review_reason: Optional[str] = None


class ReviewQueueItem(BaseModel):
    submission_id: int
    student_id: Optional[str] = None
    student_name: Optional[str] = None
    score: Optional[float] = None
    ocr_confidence: Optional[float] = None
    image_quality: Optional[float] = None
    needs_review: Optional[bool] = None
    review_reason: Optional[str] = None
    review_status: Optional[str] = None
    raw_text: Optional[str] = None
    created_at: datetime


class ReviewQueueUpdate(BaseModel):
    review_status: Optional[str] = None
    review_reason: Optional[str] = None


class ReportBin(BaseModel):
    label: str
    start: float
    end: float
    count: int
    percent: float


class ReportSummary(BaseModel):
    count: int
    mean: float
    median: float
    min: float
    max: float
    stdev: float
    pass_rate: float
    distribution: List[ReportBin] = Field(default_factory=list)



class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1)
    source_lang: str = Field("fr", min_length=2, max_length=5)
    target_lang: str = Field("en", min_length=2, max_length=5)
    provider: str = Field("google")

class TranslateResponse(BaseModel):
    translated_text: str
    provider: str
