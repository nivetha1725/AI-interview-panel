from datetime import datetime
from sqlalchemy import (create_engine, Column, Integer, String, Float, Text,
                        DateTime, ForeignKey, JSON, Boolean)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from .config import settings

engine = create_engine(settings.db, connect_args={"check_same_thread": False}
                       if settings.db.startswith("sqlite") else {})
Session = sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()

class Interview(Base):
    __tablename__ = "interviews"
    id = Column(Integer, primary_key=True)
    candidate = Column(String(120)); role = Column(String(80)); level = Column(String(30))
    itype = Column(String(30)); mode = Column(String(30)); difficulty = Column(String(10))
    duration = Column(Integer); total = Column(Integer)
    resume = Column(Text, default=""); jd = Column(Text, default="")
    state = Column(String(30), default="START")
    start_time = Column(DateTime, default=datetime.utcnow); end_time = Column(DateTime)
    overall_score = Column(Float)
    questions = relationship("Question", cascade="all,delete-orphan", order_by="Question.number")

class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"))
    number = Column(Integer); persona = Column(String(30)); text = Column(Text)
    qtype = Column(String(30)); difficulty = Column(String(10))
    topics = Column(JSON, default=list); follow_up = Column(Boolean, default=False)
    meta = Column(JSON, default=dict)  # category, purpose, max_similarity, follow-up depth
    answer = relationship("Answer", uselist=False, cascade="all,delete-orphan")

class Answer(Base):
    __tablename__ = "answers"
    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey("questions.id"))
    transcript = Column(Text); duration = Column(Float)
    content_score = Column(Float); communication_score = Column(Float)
    confidence_score = Column(Float); structure_score = Column(Float)
    filler_count = Column(Integer); tone = Column(String(20))
    analysis = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)

from sqlalchemy import inspect, text  # lightweight migration for databases created before `meta` existed
if "meta" not in [c["name"] for c in inspect(engine).get_columns("questions")]:
    with engine.begin() as _c: _c.execute(text("ALTER TABLE questions ADD COLUMN meta JSON"))
