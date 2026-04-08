from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
import datetime
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="teacher")

class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)

    classes = relationship("Class", back_populates="teacher")

class Class(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"))

    teacher = relationship("Teacher", back_populates="classes")
    subjects = relationship("Subject", back_populates="klass")

class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"))

    klass = relationship("Class", back_populates="subjects")
    submissions = relationship("Submission", back_populates="subject")

class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    student_name = Column(String, index=True)
    score = Column(Float, nullable=True)
    feedback = Column(String, nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    subject = relationship("Subject", back_populates="submissions")