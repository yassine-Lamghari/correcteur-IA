import csv
import io
import statistics

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
from app.services.pdf_generator import CoursePDFGenerator, ExamPDFGenerator
from app.models.schemas import (
    BatchGradeRequest,
    BatchStudentResult,
    CourseGenerationRequest,
    CourseResponse,
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
    WorksheetGenerationRequest,
    WorksheetResponse,
    Token
)
from app.services.feedback import FeedbackService
from app.services.glm_ocr import GLMOCRClient
from app.services.grading import GradingService
from app.services.translation import TranslationService
from app.services.export import ExportService
from fpdf import FPDF

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


# --- Students ---

@router.post("/students/", response_model=schemas.Student)
def create_student(student: schemas.StudentCreate, db: Session = Depends(get_db), current_user=Depends(require_auth)):
    existing = db.query(domain.Student).filter(domain.Student.student_code == student.student_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Student code already exists")

    db_student = domain.Student(
        student_code=student.student_code,
        full_name=student.full_name,
        email=student.email,
        class_id=student.class_id,
    )
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student


@router.post("/students/bulk", response_model=List[schemas.Student])
def bulk_create_students(payload: schemas.BulkStudentCreate, db: Session = Depends(get_db), current_user=Depends(require_auth)):
    created = []
    for item in payload.students:
        existing = db.query(domain.Student).filter(domain.Student.student_code == item.student_code).first()
        if existing:
            existing.full_name = item.full_name
            existing.email = item.email
            existing.class_id = payload.class_id
            created.append(existing)
            continue

        db_student = domain.Student(
            student_code=item.student_code,
            full_name=item.full_name,
            email=item.email,
            class_id=payload.class_id,
        )
        db.add(db_student)
        created.append(db_student)

    db.commit()
    for student in created:
        db.refresh(student)
    return created


@router.get("/students/class/{class_id}", response_model=List[schemas.Student])
def read_students_by_class(class_id: int, db: Session = Depends(get_db), current_user=Depends(require_auth)):
    return db.query(domain.Student).filter(domain.Student.class_id == class_id).all()


@router.put("/students/{student_id}", response_model=schemas.Student)
def update_student(student_id: int, payload: schemas.StudentUpdate, db: Session = Depends(get_db), current_user=Depends(require_auth)):
    student = db.query(domain.Student).filter(domain.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if payload.full_name is not None:
        student.full_name = payload.full_name
    if payload.email is not None:
        student.email = payload.email
    db.commit()
    db.refresh(student)
    return student


@router.get("/students/export/{class_id}")
def export_students(class_id: int, db: Session = Depends(get_db), current_user=Depends(require_auth)):
    students = db.query(domain.Student).filter(domain.Student.class_id == class_id).all()
    output = io.StringIO()
    output.write('\ufeff')  # Ajout du BOM UTF-8 pour Excel
    writer = csv.writer(output, delimiter=';') # Utilisation du point-virgule pour Excel (locale fr)
    writer.writerow(["student_code", "full_name", "email"])
    for student in students:
        writer.writerow([student.student_code, student.full_name, student.email or ""])

    output.seek(0)
    headers = {"Content-Disposition": "attachment; filename=students.csv"}
    return StreamingResponse(iter([output.getvalue()]), headers=headers, media_type="text/csv; charset=utf-8")


# --- Exam Sessions ---

@router.post("/exam-sessions/", response_model=schemas.ExamSession)
def create_exam_session(payload: schemas.ExamSessionCreate, db: Session = Depends(get_db), current_user=Depends(require_auth)):
    db_session = domain.ExamSession(
        subject_id=payload.subject_id,
        name=payload.name,
        exam_date=payload.exam_date,
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session


@router.get("/exam-sessions/subject/{subject_id}", response_model=List[schemas.ExamSession])
def read_exam_sessions(subject_id: int, db: Session = Depends(get_db), current_user=Depends(require_auth)):
    return db.query(domain.ExamSession).filter(domain.ExamSession.subject_id == subject_id).all()


# --- Rubrics ---

@router.post("/rubrics/", response_model=schemas.Rubric)
def create_rubric(payload: schemas.RubricCreate, db: Session = Depends(get_db), current_user=Depends(require_auth)):
    total_points = payload.total_points
    if total_points is None and payload.items:
        total_points = sum(item.max_points for item in payload.items)

    db_rubric = domain.Rubric(
        subject_id=payload.subject_id,
        name=payload.name,
        description=payload.description,
        total_points=total_points,
        is_active=payload.is_active,
    )
    db.add(db_rubric)
    db.flush()

    for idx, item in enumerate(payload.items):
        db_item = domain.RubricItem(
            rubric_id=db_rubric.id,
            question_id=item.question_id,
            question_type=item.question_type.value if hasattr(item.question_type, "value") else str(item.question_type),
            max_points=item.max_points,
            expected_answer=item.expected_answer,
            keywords=item.keywords,
            order_index=item.order_index or idx,
        )
        db.add(db_item)

    db.commit()
    db.refresh(db_rubric)
    return db_rubric


@router.get("/rubrics/subject/{subject_id}", response_model=List[schemas.Rubric])
def read_rubrics_by_subject(subject_id: int, db: Session = Depends(get_db), current_user=Depends(require_auth)):
    return db.query(domain.Rubric).filter(domain.Rubric.subject_id == subject_id).all()


@router.get("/rubrics/{rubric_id}", response_model=schemas.Rubric)
def read_rubric(rubric_id: int, db: Session = Depends(get_db), current_user=Depends(require_auth)):
    rubric = db.query(domain.Rubric).filter(domain.Rubric.id == rubric_id).first()
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")
    return rubric


@router.put("/rubrics/{rubric_id}", response_model=schemas.Rubric)
def update_rubric(rubric_id: int, payload: schemas.RubricUpdate, db: Session = Depends(get_db), current_user=Depends(require_auth)):
    rubric = db.query(domain.Rubric).filter(domain.Rubric.id == rubric_id).first()
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")

    if payload.name is not None:
        rubric.name = payload.name
    if payload.description is not None:
        rubric.description = payload.description
    if payload.is_active is not None:
        rubric.is_active = payload.is_active

    db.commit()
    db.refresh(rubric)
    return rubric


@router.put("/rubrics/{rubric_id}/items", response_model=schemas.Rubric)
def replace_rubric_items(rubric_id: int, payload: schemas.RubricItemsUpdate, db: Session = Depends(get_db), current_user=Depends(require_auth)):
    rubric = db.query(domain.Rubric).filter(domain.Rubric.id == rubric_id).first()
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")

    db.query(domain.RubricItem).filter(domain.RubricItem.rubric_id == rubric_id).delete()
    db.flush()

    for idx, item in enumerate(payload.items):
        db_item = domain.RubricItem(
            rubric_id=rubric_id,
            question_id=item.question_id,
            question_type=item.question_type.value if hasattr(item.question_type, "value") else str(item.question_type),
            max_points=item.max_points,
            expected_answer=item.expected_answer,
            keywords=item.keywords,
            order_index=item.order_index or idx,
        )
        db.add(db_item)

    rubric.total_points = sum(item.max_points for item in payload.items) if payload.items else rubric.total_points
    db.commit()
    db.refresh(rubric)
    return rubric


@router.post("/rubrics/{rubric_id}/activate", response_model=schemas.Rubric)
def activate_rubric(rubric_id: int, db: Session = Depends(get_db), current_user=Depends(require_auth)):
    rubric = db.query(domain.Rubric).filter(domain.Rubric.id == rubric_id).first()
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")

    db.query(domain.Rubric).filter(domain.Rubric.subject_id == rubric.subject_id).update({"is_active": False})
    rubric.is_active = True
    db.commit()
    db.refresh(rubric)
    return rubric

@router.post("/submissions/", response_model=schemas.Submission)
def create_submission(submission: schemas.SubmissionCreate, db: Session = Depends(get_db), current_user=Depends(require_auth)):
    db_sub = domain.Submission(
        student_id=submission.student_id,
        student_name=submission.student_name,
        score=submission.score,
        feedback=submission.feedback,
        answers=submission.answers,
        subject_id=submission.subject_id,
    )
    db.add(db_sub)
    db.commit()
    db.refresh(db_sub)

    meta_values = {
        "exam_session_id": submission.exam_session_id,
        "ocr_confidence": submission.ocr_confidence,
        "image_quality": submission.image_quality,
        "needs_review": bool(submission.needs_review),
        "review_reason": submission.review_reason,
        "review_status": "pending" if submission.needs_review else "ok",
        "raw_text": submission.raw_text,
    }
    if any(value is not None for value in meta_values.values()):
        db_meta = domain.SubmissionMeta(submission_id=db_sub.id, **meta_values)
        db.add(db_meta)
        db.commit()

    if submission.rubric_id is not None:
        rubric = db.query(domain.Rubric).filter(domain.Rubric.id == submission.rubric_id).first()
        max_score = rubric.total_points if rubric and rubric.total_points is not None else None
        if rubric and max_score is None:
            max_score = sum(item.max_points for item in rubric.items)

        db.query(domain.SubmissionGrade).filter(domain.SubmissionGrade.submission_id == db_sub.id).update({"is_current": False})
        db_grade = domain.SubmissionGrade(
            submission_id=db_sub.id,
            rubric_id=submission.rubric_id,
            score=db_sub.score or 0.0,
            max_score=max_score or 20.0,
            details={"source": "initial"},
            is_current=True,
        )
        db.add(db_grade)
        db.commit()

    return db_sub

@router.get("/submissions/subject/{subject_id}", response_model=List[schemas.Submission])
def read_submissions_by_subject(subject_id: int, db: Session = Depends(get_db), current_user=Depends(require_auth)):
    return db.query(domain.Submission).filter(domain.Submission.subject_id == subject_id).all()


# --- Review Queue / Regrading / Reporting ---

def _grade_with_rubric(items: list, answers: dict) -> tuple[float, dict]:
    total_score = 0.0
    details = {}
    for item in items:
        q_num = str(item.question_id)
        student_answer = (answers or {}).get(q_num, "")
        try:
            q_type = QuestionType(item.question_type)
        except (ValueError, TypeError):
            q_type = QuestionType.mcq

        q_spec = QuestionSpec(
            question_id=q_num,
            type=q_type,
            prompt=f"Question {q_num}",
            max_points=item.max_points,
            expected_answer=(item.expected_answer or "").strip() or None,
            keywords=item.keywords or [],
        )
        grade_res = grading_service.grade(q_spec, student_answer, use_llm=False)
        total_score += grade_res.awarded_points
        details[q_num] = {
            "awarded": grade_res.awarded_points,
            "max": item.max_points,
            "method": grade_res.method,
            "needs_review": grade_res.needs_human_review,
        }
    return round(total_score, 2), details


@router.post("/submissions/regrade", response_model=List[schemas.SubmissionGrade])
def regrade_submissions(payload: schemas.RegradeRequest, db: Session = Depends(get_db), current_user=Depends(require_auth)):
    if not payload.submission_ids and not payload.subject_id:
        raise HTTPException(status_code=400, detail="Provide submission_ids or subject_id")

    rubric = db.query(domain.Rubric).filter(domain.Rubric.id == payload.rubric_id).first()
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")

    items = sorted(rubric.items, key=lambda item: item.order_index)
    max_score = rubric.total_points if rubric.total_points is not None else sum(item.max_points for item in items)

    if payload.submission_ids:
        submissions = db.query(domain.Submission).filter(domain.Submission.id.in_(payload.submission_ids)).all()
    else:
        submissions = db.query(domain.Submission).filter(domain.Submission.subject_id == payload.subject_id).all()

    grades = []
    for sub in submissions:
        score, details = _grade_with_rubric(items, sub.answers or {})
        sub.score = score
        db.query(domain.SubmissionGrade).filter(domain.SubmissionGrade.submission_id == sub.id).update({"is_current": False})
        db_grade = domain.SubmissionGrade(
            submission_id=sub.id,
            rubric_id=rubric.id,
            score=score,
            max_score=max_score,
            details=details,
            is_current=True,
        )
        db.add(db_grade)
        grades.append(db_grade)

    db.commit()
    for grade in grades:
        db.refresh(grade)
    return grades


@router.get("/review-queue/subject/{subject_id}", response_model=List[schemas.ReviewQueueItem])
def read_review_queue(subject_id: int, db: Session = Depends(get_db), current_user=Depends(require_auth)):
    rows = (
        db.query(domain.Submission, domain.SubmissionMeta)
        .join(domain.SubmissionMeta, domain.SubmissionMeta.submission_id == domain.Submission.id)
        .filter(domain.Submission.subject_id == subject_id)
        .filter(domain.SubmissionMeta.needs_review == True)
        .filter(domain.SubmissionMeta.review_status != "resolved")
        .all()
    )

    results = []
    for submission, meta in rows:
        results.append(schemas.ReviewQueueItem(
            submission_id=submission.id,
            student_id=submission.student_id,
            student_name=submission.student_name,
            score=submission.score,
            ocr_confidence=meta.ocr_confidence,
            image_quality=meta.image_quality,
            needs_review=meta.needs_review,
            review_reason=meta.review_reason,
            review_status=meta.review_status,
            raw_text=meta.raw_text,
            created_at=submission.created_at,
        ))

    return results


@router.patch("/review-queue/{submission_id}", response_model=schemas.SubmissionMeta)
def update_review_queue(submission_id: int, payload: schemas.ReviewQueueUpdate, db: Session = Depends(get_db), current_user=Depends(require_auth)):
    meta = db.query(domain.SubmissionMeta).filter(domain.SubmissionMeta.submission_id == submission_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Submission meta not found")

    if payload.review_status is not None:
        meta.review_status = payload.review_status
    if payload.review_reason is not None:
        meta.review_reason = payload.review_reason

    db.commit()
    db.refresh(meta)
    return meta


def _compute_report(scores: list[float]) -> schemas.ReportSummary:
    if not scores:
        return schemas.ReportSummary(
            count=0,
            mean=0.0,
            median=0.0,
            min=0.0,
            max=0.0,
            stdev=0.0,
            pass_rate=0.0,
            distribution=[],
        )

    count = len(scores)
    mean = sum(scores) / count
    median = statistics.median(scores)
    min_val = min(scores)
    max_val = max(scores)
    stdev = statistics.pstdev(scores) if count > 1 else 0.0
    pass_rate = sum(1 for s in scores if s >= 10.0) / count * 100.0

    bins = [(0, 4), (4, 8), (8, 12), (12, 16), (16, 20.1)]
    dist = []
    for start, end in bins:
        label = f"{int(start)}-{int(end) if end < 20.1 else 20}"
        bin_scores = [s for s in scores if start <= s < end]
        percent = (len(bin_scores) / count * 100.0) if count else 0.0
        dist.append(schemas.ReportBin(
            label=label,
            start=start,
            end=20 if end >= 20.1 else end,
            count=len(bin_scores),
            percent=percent,
        ))

    return schemas.ReportSummary(
        count=count,
        mean=mean,
        median=median,
        min=min_val,
        max=max_val,
        stdev=stdev,
        pass_rate=pass_rate,
        distribution=dist,
    )


@router.get("/reports/subject/{subject_id}", response_model=schemas.ReportSummary)
def report_summary(subject_id: int, db: Session = Depends(get_db), current_user=Depends(require_auth)):
    submissions = db.query(domain.Submission).filter(domain.Submission.subject_id == subject_id).all()
    scores = [s.score for s in submissions if s.score is not None]
    return _compute_report(scores)


@router.get("/reports/subject/{subject_id}/pdf")
def report_pdf(subject_id: int, db: Session = Depends(get_db), current_user=Depends(require_auth)):
    submissions = db.query(domain.Submission).filter(domain.Submission.subject_id == subject_id).all()
    scores = [s.score for s in submissions if s.score is not None]
    summary = _compute_report(scores)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, "Rapport de notes", ln=True)
    pdf.ln(4)
    pdf.cell(0, 8, f"Effectif: {summary.count}", ln=True)
    pdf.cell(0, 8, f"Moyenne: {summary.mean:.2f}", ln=True)
    pdf.cell(0, 8, f"Mediane: {summary.median:.2f}", ln=True)
    pdf.cell(0, 8, f"Min: {summary.min:.2f}", ln=True)
    pdf.cell(0, 8, f"Max: {summary.max:.2f}", ln=True)
    pdf.cell(0, 8, f"Ecart-type: {summary.stdev:.2f}", ln=True)
    pdf.cell(0, 8, f"Taux de reussite: {summary.pass_rate:.1f}%", ln=True)
    pdf.ln(6)
    pdf.cell(0, 8, "Distribution:", ln=True)

    chart_x = 20
    chart_y = pdf.get_y() + 4
    bar_width = 120
    bar_height = 6
    max_percent = max([b.percent for b in summary.distribution], default=0) or 1

    for idx, bin_item in enumerate(summary.distribution):
        pdf.set_xy(chart_x, chart_y + idx * 9)
        pdf.cell(20, 6, bin_item.label)
        fill_width = int(bar_width * (bin_item.percent / max_percent))
        pdf.rect(chart_x + 22, chart_y + idx * 9, bar_width, bar_height)
        pdf.set_fill_color(76, 129, 190)
        if fill_width > 0:
            pdf.rect(chart_x + 22, chart_y + idx * 9, fill_width, bar_height, style="F")
        pdf.set_xy(chart_x + 22 + bar_width + 4, chart_y + idx * 9)
        pdf.cell(0, 6, f"{bin_item.count} ({bin_item.percent:.0f}%)")

    pdf_output = pdf.output(dest="S")
    if isinstance(pdf_output, str):
        pdf_output = pdf_output.encode("latin-1", errors="replace")
    elif isinstance(pdf_output, bytearray):
        pdf_output = bytes(pdf_output)
    headers = {"Content-Disposition": "attachment; filename=report.pdf"}
    return StreamingResponse(iter([pdf_output]), headers=headers, media_type="application/pdf")

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
def batch_grade(request: BatchGradeRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> List[BatchStudentResult]:
    results = []

    rubric_items = []
    if request.rubric_id is not None:
        db_rubric = db.query(domain.Rubric).filter(domain.Rubric.id == request.rubric_id).first()
        if not db_rubric:
            raise HTTPException(status_code=404, detail="Rubric not found")
        rubric_items = sorted(db_rubric.items, key=lambda item: item.order_index)

    for image_b64 in request.submissions:
        try:
            # 1. OCR Extract
            ocr_result = ocr_client.recognize(image_b64, OCRTask.text)

            # 2. Grade
            total_score = 0.0
            student_answers = ocr_result.extracted_answers or {}
            needs_review = False
            review_reasons = []

            if ocr_result.confidence < 0.6:
                needs_review = True
                review_reasons.append("low_ocr_confidence")
            if ocr_result.image_quality is not None and ocr_result.image_quality < 0.4:
                needs_review = True
                review_reasons.append("low_image_quality")
            if not student_answers:
                needs_review = True
                review_reasons.append("no_answers_extracted")

            if rubric_items:
                for item in rubric_items:
                    q_num = str(item.question_id)
                    student_answer = student_answers.get(q_num, "")
                    try:
                        q_type = QuestionType(item.question_type)
                    except (ValueError, TypeError):
                        q_type = QuestionType.mcq

                    q_spec = QuestionSpec(
                        question_id=q_num,
                        type=q_type,
                        prompt=f"Question {q_num}",
                        max_points=item.max_points,
                        expected_answer=(item.expected_answer or "").strip() or None,
                        keywords=item.keywords or [],
                    )
                    if student_answer.strip():
                        grade_res = grading_service.grade(q_spec, student_answer, use_llm=False)
                        total_score += grade_res.awarded_points
                        if grade_res.needs_human_review:
                            needs_review = True
                            review_reasons.append("grading_uncertain")
            else:
                num_questions = len(request.correct_answers)
                point_per_question = 20.0 / num_questions if num_questions > 0 else 0.0

                for q_num, expected_answer in request.correct_answers.items():
                    student_answer = student_answers.get(str(q_num), "")
                    if student_answer.strip():
                        q_spec = QuestionSpec(
                            question_id=str(q_num),
                            type=QuestionType.mcq,
                            prompt=f"Question {q_num}",
                            max_points=point_per_question,
                            expected_answer=expected_answer.strip(),
                            keywords=[expected_answer.strip()],
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
                raw_text=ocr_result.raw_text,
                ocr_confidence=ocr_result.confidence,
                image_quality=ocr_result.image_quality,
                needs_review=needs_review,
                review_reason=", ".join(sorted(set(review_reasons))) if review_reasons else None,
            ))

        except Exception as e:
            # Add an empty/failed result in case of OCR or grading error for this submission
            results.append(BatchStudentResult(
                student_id=None,
                student_name="Error Processing Submission",
                score=0.0,
                answers={},
                raw_text=str(e),
                needs_review=True,
                review_reason="batch_error",
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

# --- Course Generation (Gemini) ---
@router.post("/courses/generate", response_model=CourseResponse)
def generate_course(request: CourseGenerationRequest, current_user=Depends(get_current_user)):
    """
    Génère un cours complet structuré (Markdown) avec exemples et exercices via Gemini.
    """
    try:
        return gemini_service.generate_course(
            request.topic, request.instructions, request.source_material
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur interne : {str(e)}")


@router.post("/courses/export-pdf")
def export_course_pdf(course: CourseResponse, current_user=Depends(get_current_user)):
    """
    Transforme un cours (titre + Markdown) en fichier PDF téléchargeable.
    """
    try:
        pdf_bytes = CoursePDFGenerator.render_markdown_to_pdf(
            course.title, course.content_markdown
        )
        raw = bytes(pdf_bytes) if isinstance(pdf_bytes, (bytes, bytearray)) else str(pdf_bytes).encode("latin-1", errors="replace")
        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in course.title)[:80] or "Cours"
        headers = {"Content-Disposition": f'attachment; filename="{safe_name}.pdf"'}
        return StreamingResponse(
            iter([raw]),
            headers=headers,
            media_type="application/pdf",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur PDF : {str(e)}")


@router.post("/worksheets/generate", response_model=WorksheetResponse)
def generate_worksheet(request: WorksheetGenerationRequest, current_user=Depends(get_current_user)):
    """
    Génère un TD ou TP (Markdown) à partir du support de cours.
    """
    try:
        return gemini_service.generate_worksheet(
            request.course_content, request.instructions, request.worksheet_type
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur interne : {str(e)}")


@router.post("/worksheets/export-pdf")
def export_worksheet_pdf(worksheet: WorksheetResponse, current_user=Depends(get_current_user)):
    """
    Transforme un TD/TP (titre + Markdown) en fichier PDF téléchargeable.
    """
    try:
        pdf_bytes = CoursePDFGenerator.render_markdown_to_pdf(
            worksheet.title, worksheet.content_markdown
        )
        raw = bytes(pdf_bytes) if isinstance(pdf_bytes, (bytes, bytearray)) else str(pdf_bytes).encode("latin-1", errors="replace")
        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in worksheet.title)[:80] or "TD_TP"
        headers = {"Content-Disposition": f'attachment; filename="{safe_name}.pdf"'}
        return StreamingResponse(
            iter([raw]),
            headers=headers,
            media_type="application/pdf",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur PDF : {str(e)}")


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
