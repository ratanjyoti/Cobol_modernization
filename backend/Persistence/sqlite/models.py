from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum  # <--- ADD Enum HERE
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
