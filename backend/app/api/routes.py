from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.models import schemas, domain
from app.core.database import get_db
from app.models.schemas import (
    FeedbackRequest,
    FeedbackResponse,
    GradeRequest,
    GradeResult,
    OCRRequest,
    OCRResult,
    TranslateRequest,
    TranslateResponse,
)
from app.services.feedback import FeedbackService
from app.services.glm_ocr import GLMOCRClient
from app.services.grading import GradingService
from app.services.translation import TranslationService
from app.services.export import ExportService
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/v1", tags=["autograde"])

# --- Database Initialization (Auto-create tables) ---
from app.core.database import engine
domain.Base.metadata.create_all(bind=engine)
# ----------------------------------------------------

# --- CRUD for Teacher / Class / Subject / Submission ---

@router.post("/teachers/", response_model=schemas.Teacher)
def create_teacher(teacher: schemas.TeacherCreate, db: Session = Depends(get_db)):
    db_teacher = domain.Teacher(name=teacher.name, email=teacher.email)
    db.add(db_teacher)
    db.commit()
    db.refresh(db_teacher)
    return db_teacher

@router.get("/teachers/", response_model=List[schemas.Teacher])
def read_teachers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    teachers = db.query(domain.Teacher).offset(skip).limit(limit).all()
    return teachers

@router.post("/classes/", response_model=schemas.Class)
def create_class(klass: schemas.ClassCreate, db: Session = Depends(get_db)):
    db_class = domain.Class(name=klass.name, teacher_id=klass.teacher_id)
    db.add(db_class)
    db.commit()
    db.refresh(db_class)
    return db_class

@router.get("/classes/teacher/{teacher_id}", response_model=List[schemas.Class])
def read_classes_by_teacher(teacher_id: int, db: Session = Depends(get_db)):
    return db.query(domain.Class).filter(domain.Class.teacher_id == teacher_id).all()

@router.post("/subjects/", response_model=schemas.Subject)
def create_subject(subject: schemas.SubjectCreate, db: Session = Depends(get_db)):
    db_subject = domain.Subject(name=subject.name, class_id=subject.class_id)
    db.add(db_subject)
    db.commit()
    db.refresh(db_subject)
    return db_subject

@router.get("/subjects/class/{class_id}", response_model=List[schemas.Subject])
def read_subjects_by_class(class_id: int, db: Session = Depends(get_db)):
    return db.query(domain.Subject).filter(domain.Subject.class_id == class_id).all()

@router.post("/submissions/", response_model=schemas.Submission)
def create_submission(submission: schemas.SubmissionCreate, db: Session = Depends(get_db)):
    db_sub = domain.Submission(
        student_name=submission.student_name,
        score=submission.score,
        feedback=submission.feedback,
        subject_id=submission.subject_id
    )
    db.add(db_sub)
    db.commit()
    db.refresh(db_sub)
    return db_sub

@router.get("/submissions/subject/{subject_id}", response_model=List[schemas.Submission])
def read_submissions_by_subject(subject_id: int, db: Session = Depends(get_db)):
    return db.query(domain.Submission).filter(domain.Submission.subject_id == subject_id).all()

# --- Existing Endpoints ---

ocr_client = GLMOCRClient()
grading_service = GradingService()
feedback_service = FeedbackService()
translation_service = TranslationService()


@router.post("/ocr", response_model=OCRResult)
def ocr(request: OCRRequest) -> OCRResult:
    return ocr_client.recognize(request.image_base64, request.task)


@router.post("/grade", response_model=GradeResult)
def grade(request: GradeRequest) -> GradeResult:
    return grading_service.grade(request.question, request.student_answer, use_llm=request.use_llm)


@router.post("/feedback", response_model=FeedbackResponse)
def feedback(request: FeedbackRequest) -> FeedbackResponse:
    text = feedback_service.generate(request)
    return FeedbackResponse(feedback=text)


@router.post("/translate", response_model=TranslateResponse)
def translate(request: TranslateRequest) -> TranslateResponse:
    return translation_service.translate(request)

@router.get("/export/excel/{subject_id}")
def export_excel(subject_id: int, db: Session = Depends(get_db)):
    subject = db.query(domain.Subject).filter(domain.Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Matière introuvable")
        
    klass = db.query(domain.Class).filter(domain.Class.id == subject.class_id).first()
    class_name = klass.name if klass else "Inconnue"
    
    submissions = db.query(domain.Submission).filter(domain.Submission.subject_id == subject_id).all()
    
    excel_file = ExportService.generate_excel(submissions, subject, class_name)
    
    headers = {
        'Content-Disposition': f'attachment; filename="notes_{subject.name.replace(" ", "_")}.xlsx"'
    }
    
    return StreamingResponse(
        excel_file,
        headers=headers,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
