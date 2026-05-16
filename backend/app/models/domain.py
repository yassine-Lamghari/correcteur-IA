import datetime

from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, JSON, String, DateTime, Text
from sqlalchemy.orm import relationship

from app.core.database import Base

class User(Base):
    """
    User model representing an application user (e.g., teacher).
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="teacher")

    classes = relationship("Class", back_populates="user")

class Class(Base):
    """
    Class model representing a course class or student group.
    """
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="classes")
    subjects = relationship("Subject", back_populates="course_class")
    students = relationship("Student", back_populates="course_class")

class Subject(Base):
    """
    Subject model representing a specific subject within a course class.
    """
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"))

    course_class = relationship("Class", back_populates="subjects")
    submissions = relationship("Submission", back_populates="subject")
    rubrics = relationship("Rubric", back_populates="subject")
    exam_sessions = relationship("ExamSession", back_populates="subject")


class Student(Base):
    """
    Student model for roster management.
    """
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    student_code = Column(String, unique=True, index=True)
    full_name = Column(String, index=True)
    email = Column(String, nullable=True)
    class_id = Column(Integer, ForeignKey("classes.id"))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    course_class = relationship("Class", back_populates="students")


class Rubric(Base):
    """
    Rubric model for grading rules per subject.
    """
    __tablename__ = "rubrics"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    total_points = Column(Float, nullable=True)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    subject = relationship("Subject", back_populates="rubrics")
    items = relationship("RubricItem", back_populates="rubric", cascade="all, delete-orphan")


class RubricItem(Base):
    """
    Rubric item for a single question.
    """
    __tablename__ = "rubric_items"

    id = Column(Integer, primary_key=True, index=True)
    rubric_id = Column(Integer, ForeignKey("rubrics.id"))
    question_id = Column(String, index=True)
    question_type = Column(String)
    max_points = Column(Float)
    expected_answer = Column(String, nullable=True)
    keywords = Column(JSON, nullable=True)
    order_index = Column(Integer, default=0)

    rubric = relationship("Rubric", back_populates="items")


class ExamSession(Base):
    """
    Exam session to group submissions for a subject.
    """
    __tablename__ = "exam_sessions"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    name = Column(String, index=True)
    exam_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    subject = relationship("Subject", back_populates="exam_sessions")

class Submission(Base):
    """
    Submission model representing a student's answer submission for a subject.
    """
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, index=True, nullable=True)
    student_name = Column(String, index=True)
    score = Column(Float, nullable=True)
    feedback = Column(String, nullable=True)
    answers = Column(JSON, nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    subject = relationship("Subject", back_populates="submissions")
    meta = relationship("SubmissionMeta", back_populates="submission", uselist=False)
    grades = relationship("SubmissionGrade", back_populates="submission")


class SubmissionMeta(Base):
    """
    Extra metadata for submissions (OCR confidence, image quality, review).
    """
    __tablename__ = "submission_meta"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), unique=True)
    exam_session_id = Column(Integer, ForeignKey("exam_sessions.id"), nullable=True)
    ocr_confidence = Column(Float, nullable=True)
    image_quality = Column(Float, nullable=True)
    needs_review = Column(Boolean, default=False)
    review_reason = Column(String, nullable=True)
    review_status = Column(String, default="pending")
    raw_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    submission = relationship("Submission", back_populates="meta")


class SubmissionGrade(Base):
    """
    Grade history for a submission across rubrics.
    """
    __tablename__ = "submission_grades"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"))
    rubric_id = Column(Integer, ForeignKey("rubrics.id"))
    score = Column(Float)
    max_score = Column(Float)
    details = Column(JSON, nullable=True)
    is_current = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    submission = relationship("Submission", back_populates="grades")
    rubric = relationship("Rubric")