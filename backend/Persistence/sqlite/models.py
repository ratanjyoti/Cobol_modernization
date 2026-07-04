from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text  # <--- ADD Enum HERE
from sqlalchemy.ext.declarative import declarative_base
import enum  # This is the python module for the class definition
import datetime

Base = declarative_base()

# 1. Define the Python Enum class using the 'enum' module
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
    
    # Configuration
    llm_provider = Column(String)
    llm_model = Column(String)
    interaction_lang = Column(String)
    
    # Performance Profile
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
    
    # Use the SQLAlchemy Enum type here. 
    # Because we imported 'Enum' from sqlalchemy, this now works.
    status = Column(Enum(FileStatus), default=FileStatus.PENDING_CONFIRMATION)

class ProjectComplexity(Base):
    __tablename__ = "project_complexity"
    run_id = Column(String, ForeignKey("projects.run_id"), primary_key=True)
    score = Column(Integer)
    tier = Column(String) # Low, Medium, High
    reasoning_effort = Column(String) # Turbo, Fast, Balanced, Thorough

class FileChunk(Base):
    __tablename__ = "file_chunks"
    id = Column(Integer, primary_key=True)
    run_id = Column(String, ForeignKey("projects.run_id"), nullable=False)
    file_id = Column(Integer, ForeignKey("project_files.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False) # Chunk 0, 1, 2...
    content = Column(Text, nullable=False)
    start_line = Column(Integer)
    end_line = Column(Integer)
    overlap_content = Column(Text) # The 300 lines from previous chunk

class FileRelation(Base):
    __tablename__ = "file_relations"
    
    id = Column(Integer, primary_key=True)
    run_id = Column(String, ForeignKey("projects.run_id"), nullable=False)
    source_file = Column(String, nullable=False) # e.g., 'ACCOUNT.cbl'
    target_item = Column(String, nullable=False) # e.g., 'CUST-PROC' or 'CUST_TABLE'
    relation_type = Column(String, nullable=False) # 'CALLS', 'INCLUDES', 'READS_WRITES'
