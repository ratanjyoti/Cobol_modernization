from sqlalchemy.ext.declarative import declarative_base
import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, Enum
import enum

Base = declarative_base()

class FileStatus(enum.Enum):
    PENDING_CONFIRMATION = "PENDING_CONFIRMATION"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"

class ProjectFile(Base):
    __tablename__ = "project_files"
    id = Column(Integer, primary_key=True)
    run_id = Column(String, ForeignKey("projects.run_id"), nullable=False)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False) # Relative path in the project
    detected_lang = Column(String)           # COBOL, JCL, TELON
    status = Column(Enum(FileStatus), default=FileStatus.PENDING_CONFIRMATION)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)

class Project(Base):
    __tablename__ = "projects"
    run_id = Column(String, primary_key=True) # UUID
    user_id = Column(Integer, ForeignKey("users.id"))
    project_name = Column(String)
    
    # Configuration
    llm_provider = Column(String)        # 'azure' or 'ollama'
    llm_model = Column(String)          # 'gpt-4o', 'codellama', etc.
    interaction_lang = Column(String)   # 'en', 'hi', 'jp'
    
    # Performance Profile
    speed_profile = Column(String)      # 'Turbo', 'Fast', 'Balanced', 'Thorough'
    reasoning_effort = Column(String)   # 'Low', 'Medium', 'High'
    parallel_workers = Column(Integer)   # 1 to 10
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
