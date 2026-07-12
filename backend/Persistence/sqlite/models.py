from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text
from sqlalchemy.ext.declarative import declarative_base
import enum
import datetime

Base = declarative_base()


class FileStatus(enum.Enum):
    PENDING_CONFIRMATION = "PENDING_CONFIRMATION"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)


class Project(Base):
    __tablename__ = "projects"
    run_id = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    project_name = Column(String)

    llm_provider = Column(String)
    llm_model = Column(String)
    interaction_lang = Column(String)

    speed_profile = Column(String)
    reasoning_effort = Column(String)
    parallel_workers = Column(Integer)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ProjectFile(Base):
    __tablename__ = "project_files"
    id = Column(Integer, primary_key=True)
    run_id = Column(String, ForeignKey("projects.run_id"), nullable=False)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    detected_lang = Column(String)
    status = Column(Enum(FileStatus), default=FileStatus.PENDING_CONFIRMATION)


class ProjectComplexity(Base):
    __tablename__ = "project_complexity"
    run_id = Column(String, ForeignKey("projects.run_id"), primary_key=True)
    score = Column(Integer)
    tier = Column(String)
    reasoning_effort = Column(String)


class FileComplexity(Base):
    __tablename__ = "file_complexity"
    id = Column(Integer, primary_key=True)
    run_id = Column(String, ForeignKey("projects.run_id"), nullable=False)
    file_id = Column(Integer, ForeignKey("project_files.id"), nullable=True)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    score = Column(Integer)
    tier = Column(String)
    effort = Column(String)
    mode = Column(String)
    multiplier = Column(Float)
    calculation = Column(Text)
    logic_count = Column(Integer, default=0)
    table_count = Column(Integer, default=0)
    table_bonus = Column(Integer, default=0)
    if_count = Column(Integer, default=0)
    perform_until_count = Column(Integer, default=0)
    perform_varying_count = Column(Integer, default=0)
    evaluate_count = Column(Integer, default=0)


class FileChunk(Base):
    __tablename__ = "file_chunks"
    id = Column(Integer, primary_key=True)
    run_id = Column(String, ForeignKey("projects.run_id"), nullable=False)
    file_id = Column(Integer, ForeignKey("project_files.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    start_line = Column(Integer)
    end_line = Column(Integer)
    overlap_content = Column(Text)


class FileRelation(Base):
    __tablename__ = "file_relations"
    id = Column(Integer, primary_key=True)
    run_id = Column(String, ForeignKey("projects.run_id"), nullable=False)
    source_file = Column(String, nullable=False)
    target_item = Column(String, nullable=False)
    relation_type = Column(String, nullable=False)
