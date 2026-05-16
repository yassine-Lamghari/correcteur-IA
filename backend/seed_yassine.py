import os
from datetime import datetime


USERNAME = "yassine"
EMAIL = "yassine@example.com"
PASSWORD = "yassin123"
CLASS_NAME = "Licence Info L1"
SUBJECTS = ["Mathematiques", "Physique", "Informatique"]

STUDENTS = [
    ("YAS001", "Ahmed El Amrani", "ahmed.elamrani@example.com"),
    ("YAS002", "Sara Benali", "sara.benali@example.com"),
    ("YAS003", "Omar El Idrissi", "omar.elidrissi@example.com"),
    ("YAS004", "Nadia Karim", "nadia.karim@example.com"),
    ("YAS005", "Hicham Lahlou", "hicham.lahlou@example.com"),
    ("YAS006", "Lina Haddad", "lina.haddad@example.com"),
    ("YAS007", "Youssef Amine", "youssef.amine@example.com"),
    ("YAS008", "Imane Zaki", "imane.zaki@example.com"),
    ("YAS009", "Rachid Bensaid", "rachid.bensaid@example.com"),
    ("YAS010", "Meryem Saidi", "meryem.saidi@example.com"),
    ("YAS011", "Kamal Fares", "kamal.fares@example.com"),
    ("YAS012", "Nour El Khatib", "nour.elkhatib@example.com"),
    ("YAS013", "Salma Othman", "salma.othman@example.com"),
    ("YAS014", "Hassan Rami", "hassan.rami@example.com"),
    ("YAS015", "Amina Selim", "amina.selim@example.com"),
    ("YAS016", "Amir Nabil", "amir.nabil@example.com"),
    ("YAS017", "Dina Bouchra", "dina.bouchra@example.com"),
    ("YAS018", "Samir Jalil", "samir.jalil@example.com"),
    ("YAS019", "Asmae Rahim", "asmae.rahim@example.com"),
    ("YAS020", "Rania Hadi", "rania.hadi@example.com"),
    ("YAS021", "Bilal Farid", "bilal.farid@example.com"),
    ("YAS022", "Sami Nasser", "sami.nasser@example.com"),
    ("YAS023", "Hanae Latif", "hanae.latif@example.com"),
    ("YAS024", "Tariq Mounir", "tariq.mounir@example.com"),
    ("YAS025", "Ismail Jamal", "ismail.jamal@example.com"),
]

SUBMISSIONS = [
    ("YAS001", "Ahmed El Amrani", 14.5, False, None),
    ("YAS002", "Sara Benali", 11.0, True, "low_ocr_confidence"),
    ("YAS003", "Omar El Idrissi", 17.0, False, None),
    ("YAS004", "Nadia Karim", 9.5, True, "name_mismatch"),
    ("YAS005", "Hicham Lahlou", 13.0, False, None),
    ("YAS006", "Lina Haddad", 12.5, True, "missing_student_name"),
    ("YAS007", "Youssef Amine", 15.0, False, None),
    ("YAS008", "Imane Zaki", 10.0, True, "low_image_quality"),
]


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


def main():
    os.chdir(os.path.dirname(__file__))

    from app.core.auth import get_password_hash
    from app.core.database import SessionLocal, engine
    from app.models import domain

    domain.Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        user, created_user = _get_or_create(
            session,
            domain.User,
            defaults={
                "email": EMAIL,
                "hashed_password": get_password_hash(PASSWORD),
                "role": "teacher",
            },
            username=USERNAME,
        )
        if not created_user:
            user.email = EMAIL
            user.hashed_password = get_password_hash(PASSWORD)
            session.commit()

        course_class, created_class = _get_or_create(
            session,
            domain.Class,
            defaults={"user_id": user.id},
            name=CLASS_NAME,
            user_id=user.id,
        )

        created_subjects = 0
        subject_map = {}
        for name in SUBJECTS:
            subject, created = _get_or_create(
                session,
                domain.Subject,
                defaults={"class_id": course_class.id},
                name=name,
                class_id=course_class.id,
            )
            subject_map[name] = subject
            if created:
                created_subjects += 1

        created_students = 0
        for code, name, email in STUDENTS:
            existing = session.query(domain.Student).filter(domain.Student.student_code == code).first()
            if existing:
                continue
            student = domain.Student(
                student_code=code,
                full_name=name,
                email=email,
                class_id=course_class.id,
            )
            session.add(student)
            created_students += 1
        if created_students:
            session.commit()

        subject_for_submissions = subject_map[SUBJECTS[0]]
        created_submissions = 0
        for code, name, score, needs_review, reason in SUBMISSIONS:
            existing = (
                session.query(domain.Submission)
                .filter(domain.Submission.subject_id == subject_for_submissions.id)
                .filter(domain.Submission.student_id == code)
                .first()
            )
            if existing:
                continue

            submission = domain.Submission(
                student_id=code,
                student_name=name,
                score=score,
                feedback="Initial",
                answers={"1": "A", "2": "C", "3": "B"},
                subject_id=subject_for_submissions.id,
                created_at=datetime.utcnow(),
            )
            session.add(submission)
            session.commit()
            session.refresh(submission)

            meta = domain.SubmissionMeta(
                submission_id=submission.id,
                ocr_confidence=0.65 if needs_review else 0.92,
                image_quality=0.85,
                needs_review=needs_review,
                review_reason=reason,
                review_status="pending" if needs_review else "ok",
                raw_text="OCR demo text for real data",
            )
            session.add(meta)
            session.commit()
            created_submissions += 1

        print("Realistic data ready")
        print(f"User: {user.username} (created: {created_user})")
        print(f"Class: {course_class.name} (created: {created_class})")
        print(f"Subjects created: {created_subjects}")
        print(f"Students created: {created_students}")
        print(f"Submissions created: {created_submissions}")
        print(f"Login: {USERNAME} / {PASSWORD}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
