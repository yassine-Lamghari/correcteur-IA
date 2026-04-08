from enum import Enum
from typing import List, Optional
from datetime import datetime

from pydantic import BaseModel, Field

class BaseSchema(BaseModel):
    class Config:
        from_attributes = True

class TeacherBase(BaseSchema):
    name: str
    email: str

class TeacherCreate(TeacherBase):
    pass

class Teacher(TeacherBase):
    id: int

class ClassBase(BaseSchema):
    name: str

class ClassCreate(ClassBase):
    teacher_id: int

class Class(ClassBase):
    id: int
    teacher_id: int

class SubjectBase(BaseSchema):
    name: str

class SubjectCreate(SubjectBase):
    class_id: int

class Subject(SubjectBase):
    id: int
    class_id: int

class SubmissionBase(BaseSchema):
    student_name: str
    score: Optional[float] = None
    feedback: Optional[str] = None

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
    max_points: float = Field(ge=0)
    expected_answer: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)


class OCRRequest(BaseModel):
    image_base64: str
    task: OCRTask = OCRTask.text


class OCRResult(BaseModel):
    raw_text: str
    confidence: float = Field(ge=0, le=1)
    extracted_answers: List[str] = Field(default_factory=list)


class GradeRequest(BaseModel):
    question: QuestionSpec
    student_answer: str
    use_llm: bool = False


class GradeResult(BaseModel):
    awarded_points: float
    confidence: float = Field(ge=0, le=1)
    method: str
    needs_human_review: bool


class FeedbackRequest(BaseModel):
    question: QuestionSpec
    student_answer: str
    grade: GradeResult


class FeedbackResponse(BaseModel):
    feedback: str


class TranslateRequest(BaseModel):
    text: str
    source_lang: str = "fr"
    target_lang: str = "en"


class TranslateResponse(BaseModel):
    translated_text: str
    provider: str
