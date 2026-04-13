from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse
from typing import List, Dict
from datetime import timedelta

from app.models import schemas, domain
from app.core.database import get_db
from app.core.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    require_auth,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.services.pdf_generator import ExamPDFGenerator
from app.models.schemas import (
    BatchGradeRequest,
    BatchStudentResult,
    FeedbackRequest,
    FeedbackResponse,
    ExamGenerationRequest,
    ExamResponse,
    GradeRequest,
    GradeResult,
    OCRRequest,
    OCRResult,
    OCRTask,
    QuestionSpec,
    QuestionType,
    TranslateRequest,
    TranslateResponse,
    UserCreate,
    User as UserSchema,
    Token
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

# --- Auth Routes ---
@router.post("/auth/register", response_model=UserSchema, tags=["auth"])
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(domain.User).filter((domain.User.username == user.username) | (domain.User.email == user.email)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = domain.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        role="teacher"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/auth/login", response_model=Token, tags=["auth"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(domain.User).filter(domain.User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/auth/me", response_model=UserSchema, tags=["auth"])
def get_current_user(token_data: dict = Depends(require_auth), db: Session = Depends(get_db)):
    user = db.query(domain.User).filter(domain.User.username == token_data.get("sub")).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# --- CRUD for Class / Subject / Submission ---

@router.post("/classes/", response_model=schemas.Class)
def create_class(course_class: schemas.ClassCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    db_class = domain.Class(name=course_class.name, user_id=current_user.id)
    db.add(db_class)
    db.commit()
    db.refresh(db_class)
    return db_class

@router.get("/classes/me", response_model=List[schemas.Class])
def read_my_classes(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return db.query(domain.Class).filter(domain.Class.user_id == current_user.id).all()

@router.post("/subjects/", response_model=schemas.Subject)
def create_subject(subject: schemas.SubjectCreate, db: Session = Depends(get_db), current_user=Depends(require_auth)):
    db_subject = domain.Subject(name=subject.name, class_id=subject.class_id)
    db.add(db_subject)
    db.commit()
    db.refresh(db_subject)
    return db_subject

@router.get("/subjects/class/{class_id}", response_model=List[schemas.Subject])
def read_subjects_by_class(class_id: int, db: Session = Depends(get_db), current_user=Depends(require_auth)):
    return db.query(domain.Subject).filter(domain.Subject.class_id == class_id).all()

@router.post("/submissions/", response_model=schemas.Submission)
def create_submission(submission: schemas.SubmissionCreate, db: Session = Depends(get_db), current_user=Depends(require_auth)):
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
def read_submissions_by_subject(subject_id: int, db: Session = Depends(get_db), current_user=Depends(require_auth)):
    return db.query(domain.Submission).filter(domain.Submission.subject_id == subject_id).all()

# --- Existing Endpoints ---

ocr_client = GLMOCRClient()
grading_service = GradingService()
feedback_service = FeedbackService()
translation_service = TranslationService()
from app.services.gemini import GeminiCorrector
gemini_service = GeminiCorrector()


@router.post("/ocr", response_model=OCRResult)
def ocr(request: OCRRequest, current_user=Depends(get_current_user)) -> OCRResult:
    return ocr_client.recognize(request.image_base64, request.task)


@router.post("/grade", response_model=GradeResult)
def grade(request: GradeRequest, current_user=Depends(get_current_user)) -> GradeResult:
    return grading_service.grade(request.question, request.student_answer, use_llm=request.use_llm)


@router.post("/feedback", response_model=FeedbackResponse)
def feedback(request: FeedbackRequest, current_user=Depends(get_current_user)) -> FeedbackResponse:
    text = feedback_service.generate(request)
    return FeedbackResponse(feedback=text)


@router.post("/translate", response_model=TranslateResponse)
def translate(request: TranslateRequest, current_user=Depends(get_current_user)) -> TranslateResponse:
    return translation_service.translate(request)


@router.post("/batch-grade", response_model=List[BatchStudentResult])
def batch_grade(request: BatchGradeRequest, current_user=Depends(get_current_user)) -> List[BatchStudentResult]:
    results = []

    for image_b64 in request.submissions:
        try:
            # 1. OCR Extract
            ocr_result = ocr_client.recognize(image_b64, OCRTask.text)

            # 2. Grade
            total_score = 0.0
            student_answers = ocr_result.extracted_answers or {}
            
            num_questions = len(request.correct_answers)
            point_per_question = 20.0 / num_questions if num_questions > 0 else 0.0

            for q_num, expected_answer in request.correct_answers.items():
                student_answer = student_answers.get(str(q_num), "")
                if student_answer.strip():
                    # Use mcq type for MCQ answers (single-letter A/B/C/D)
                    q_spec = QuestionSpec(
                        question_id=str(q_num),
                        type=QuestionType.mcq,
                        prompt=f"Question {q_num}",
                        max_points=point_per_question,
                        expected_answer=expected_answer.strip(),
                        keywords=[expected_answer.strip()]
                    )
                    grade_res = grading_service.grade(q_spec, student_answer, use_llm=False)
                    total_score += grade_res.awarded_points

            total_score = round(total_score, 2)

            # 3. Create Summary
            results.append(BatchStudentResult(
                student_id=ocr_result.student_id,
                student_name=ocr_result.student_name,
                score=total_score,
                answers=student_answers,
                raw_text=ocr_result.raw_text
            ))

        except Exception as e:
            # Add an empty/failed result in case of OCR or grading error for this submission
            results.append(BatchStudentResult(
                student_id=None,
                student_name="Error Processing Submission",
                score=0.0,
                answers={},
                raw_text=str(e)
            ))

    return results

@router.get("/export/excel/{subject_id}")
def export_excel(subject_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    subject = db.query(domain.Subject).filter(domain.Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
        
    course_class = db.query(domain.Class).filter(domain.Class.id == subject.class_id).first()
    class_name = course_class.name if course_class else "Unknown"
    
    submissions = db.query(domain.Submission).filter(domain.Submission.subject_id == subject_id).all()
    
    excel_file = ExportService.generate_excel(submissions, subject, class_name)
    
    headers = {
        'Content-Disposition': f'attachment; filename="grades_{subject.name.replace(" ", "_")}.xlsx"'
    }
    
    return StreamingResponse(
        excel_file,
        headers=headers,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

# --- Exam Generation Routes ---
@router.post("/exams/generate", response_model=ExamResponse)
def generate_exam(request: ExamGenerationRequest, current_user=Depends(get_current_user)):
    """
    Generate an MCQ exam based on the provided context.
    """
    try:
        exam = gemini_service.generate_exam(request.course_content, request.instructions, request.num_questions)
        return exam
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.post("/exams/export-pdfs")
def export_exam_pdfs(exam: ExamResponse):
    """
    Accepts the validated ExamResponse JSON and returns a ZIP containing 3 PDFs.
    """
    try:
        exam_dict = exam.model_dump()
        zip_buffer = ExamPDFGenerator.create_exam_zip(exam_dict)
        headers = {
            'Content-Disposition': 'attachment; filename="Examen_QCM_et_Reponses.zip"'
        }
        return StreamingResponse(
            zip_buffer,
            headers=headers,
            media_type="application/zip"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"PDF Generation error: {str(e)}")
