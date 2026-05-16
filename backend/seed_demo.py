import os
from datetime import datetime


DEMO_USERNAME = "demo"
DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demo123"
DEMO_CLASS_NAME = "Demo Class"
DEMO_SUBJECT_NAME = "Demo Subject"


def _get_or_create(session, model, defaults=None, **filters):
    instance = session.query(model).filter_by(**filters).first()
    if instance:
        return instance, False
    params = {}
    if defaults:
        params.update(defaults)
    params.update(filters)
    instance = model(**params)
    session.add(instance)
    session.commit()
    session.refresh(instance)
    return instance, True


def _ensure_demo_students(session, domain, class_id):
    students = [
        ("S001", "Ali Ben", "ali.ben@example.com"),
        ("S002", "Sara Karim", "sara.karim@example.com"),
        ("S003", "Hassan Yass", "hassan.yass@example.com"),
        ("S004", "Lina Amr", "lina.amr@example.com"),
        ("S005", "Omar Salim", "omar.salim@example.com"),
        ("S006", "Nora Adel", "nora.adel@example.com"),
        ("S007", "Kamal Rami", "kamal.rami@example.com"),
        ("S008", "Maya Nabil", "maya.nabil@example.com"),
        ("S009", "Rami Zaki", "rami.zaki@example.com"),
        ("S010", "Yara Sami", "yara.sami@example.com"),
    ]

    created = 0
    for code, name, email in students:
        existing = session.query(domain.Student).filter(domain.Student.student_code == code).first()
        if existing:
            continue
        student = domain.Student(
            student_code=code,
            full_name=name,
            email=email,
            class_id=class_id,
        )
        session.add(student)
        created += 1
    if created:
        session.commit()
    return created


def _ensure_demo_submissions(session, domain, subject_id):
    submissions = [
        ("S001", "Ali Ben", 15.5, False, None),
        ("S002", "Sara Karim", 12.0, True, "name_from_student_list"),
        ("S003", "Hassan Yass", 18.0, False, None),
        ("S004", "Lina Amr", 9.5, True, "low_ocr_confidence"),
        ("S005", "Omar Salim", 14.0, False, None),
        ("S006", "Nora Adel", 11.0, True, "name_mismatch"),
    ]

    created = 0
    for code, name, score, needs_review, reason in submissions:
        existing = (
            session.query(domain.Submission)
            .filter(domain.Submission.subject_id == subject_id)
            .filter(domain.Submission.student_id == code)
            .first()
        )
        if existing:
            continue

        submission = domain.Submission(
            student_id=code,
            student_name=name,
            score=score,
            feedback="Demo",
            answers={"1": "A", "2": "B", "3": "C"},
            subject_id=subject_id,
            created_at=datetime.utcnow(),
        )
        session.add(submission)
        session.commit()
        session.refresh(submission)

        meta = domain.SubmissionMeta(
            submission_id=submission.id,
            ocr_confidence=0.78 if needs_review else 0.92,
            image_quality=0.85,
            needs_review=needs_review,
            review_reason=reason,
            review_status="pending" if needs_review else "ok",
            raw_text="Demo OCR text",
        )
        session.add(meta)
        session.commit()
        created += 1

    return created


def main():
    # Ensure database path is consistent with backend
    os.chdir(os.path.dirname(__file__))

    from app.core.auth import get_password_hash
    from app.core.database import SessionLocal, engine
    from app.models import domain

    domain.Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        demo_user, created_user = _get_or_create(
            session,
            domain.User,
            defaults={
                "email": DEMO_EMAIL,
                "hashed_password": get_password_hash(DEMO_PASSWORD),
                "role": "teacher",
            },
            username=DEMO_USERNAME,
        )

        demo_class, created_class = _get_or_create(
            session,
            domain.Class,
            defaults={"user_id": demo_user.id},
            name=DEMO_CLASS_NAME,
            user_id=demo_user.id,
        )

        demo_subject, created_subject = _get_or_create(
            session,
            domain.Subject,
            defaults={"class_id": demo_class.id},
            name=DEMO_SUBJECT_NAME,
            class_id=demo_class.id,
        )

        created_students = _ensure_demo_students(session, domain, demo_class.id)
        created_submissions = _ensure_demo_submissions(session, domain, demo_subject.id)

        print("Demo data ready")
        print(f"User: {demo_user.username} (created: {created_user})")
        print(f"Class: {demo_class.name} (created: {created_class})")
        print(f"Subject: {demo_subject.name} (created: {created_subject})")
        print(f"Students created: {created_students}")
        print(f"Submissions created: {created_submissions}")
        print(f"Login: {DEMO_USERNAME} / {DEMO_PASSWORD}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
