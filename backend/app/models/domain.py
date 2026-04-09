import datetime

from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
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

class Submission(Base):
    """
    Submission model representing a student's answer submission for a subject.
    """
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    student_name = Column(String, index=True)
    score = Column(Float, nullable=True)
    feedback = Column(String, nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    subject = relationship("Subject", back_populates="submissions")