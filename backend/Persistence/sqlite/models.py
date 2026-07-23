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
    ai_mode = Column(String)
    custom_api_key = Column(String, nullable=True)
    custom_api_base_url = Column(String, nullable=True)
    llm_model = Column(String)
    local_provider = Column(String, nullable=True)
    interaction_lang = Column(String)

    neo4j_uri = Column(String, nullable=True)
    neo4j_user = Column(String, nullable=True)
    neo4j_password = Column(String, nullable=True)

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

class ChunkAnalysis(Base):
    __tablename__ = "chunk_analysis"
    
    id = Column(Integer, primary_key=True)
    chunk_id = Column(Integer, ForeignKey("file_chunks.id"), nullable=False)
    run_id = Column(String, nullable=False)
    technical_yaml = Column(Text, nullable=False) # The structured blueprint (The "How")
    analysis_status = Column(String, default="COMPLETED") # COMPLETED, FAILED
    tokens_used = Column(Integer)

class BusinessRule(Base):
    __tablename__ = "business_rules"
    id = Column(Integer, primary_key=True)
    run_id = Column(String, ForeignKey("projects.run_id"), nullable=False)
    
    # New Fields for the "Report" style
    business_purpose = Column(Text)  # The high-level purpose
    functional_logic = Column(Text) # The detailed breakdown
    business_logic = Column(Text) # Backward-compatible storage for the detailed flow
    
    chunk_id = Column(Integer, ForeignKey("file_chunks.id"), nullable=True)
    file_id = Column(Integer, ForeignKey("project_files.id"), nullable=True)
    chunk_index = Column(Integer)
    rule_id = Column(String) 
    rule_text = Column(Text, nullable=True) 
    technical_ref = Column(Text)
    status = Column(String, default="PENDING")
    technical_yaml = Column(Text)

    
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
    semantic_units = Column(Text)
    converted_code = Column(Text)
    summary = Column(Text)
    tokens_used = Column(Integer, default=0)
    processing_time = Column(Float, default=0)
    status = Column(String, default="PENDING")
    error_message = Column(Text)


class TypeMappingTable(Base):
    __tablename__ = "type_mapping_table"
    id = Column(Integer, primary_key=True)
    run_id = Column(String, ForeignKey("projects.run_id"), nullable=False)
    file_id = Column(Integer, ForeignKey("project_files.id"), nullable=True)
    legacy_variable = Column(String, nullable=False)
    legacy_type = Column(String)
    target_type = Column(String)
    target_field_name = Column(String)


class SignatureRegistry(Base):
    __tablename__ = "signature_registry"
    id = Column(Integer, primary_key=True)
    run_id = Column(String, ForeignKey("projects.run_id"), nullable=False)
    file_id = Column(Integer, ForeignKey("project_files.id"), nullable=True)
    legacy_name = Column(String, nullable=False)
    target_method_name = Column(String)
    target_signature = Column(String)
    converted_chunk_index = Column(Integer, nullable=True)


class ConsistencyDiscrepancy(Base):
    __tablename__ = "consistency_discrepancies"
    id = Column(Integer, primary_key=True)
    run_id = Column(String, ForeignKey("projects.run_id"), nullable=False)
    file_id = Column(Integer, ForeignKey("project_files.id"), nullable=True)
    chunk_index = Column(Integer, nullable=True)
    discrepancy_type = Column(String, nullable=False)
    legacy_name = Column(String)
    expected_value = Column(Text)
    actual_value = Column(Text)
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class FileRelation(Base):
    __tablename__ = "file_relations"
    id = Column(Integer, primary_key=True)
    run_id = Column(String, ForeignKey("projects.run_id"), nullable=False)
    source_file = Column(String, nullable=False)
    target_item = Column(String, nullable=False)
    relation_type = Column(String, nullable=False)

class TechnicalAnalysis(Base):
    __tablename__ = "technical_analysis"
    id = Column(Integer, primary_key=True)
    run_id = Column(String, ForeignKey("projects.run_id"))
    file_id = Column(Integer, ForeignKey("project_files.id"))
    filename = Column(String)
    report_json = Column(Text) # Stores the TechnicalAnalysisReport as JSON

class FileAnalysis(Base):
    __tablename__ = "file_analysis"
    id = Column(Integer, primary_key=True)
    run_id = Column(String, ForeignKey("projects.run_id"), nullable=False)
    file_id = Column(Integer, ForeignKey("project_files.id"), nullable=False)
    
    # --- Business Section ---
    business_purpose = Column(Text) # e.g., "The program serves as a payroll application..."
    functional_summary = Column(Text) # Detailed flow narrative
    
    # --- Technical Section (Stored as JSON for flexibility) ---
    # Stores: Data Structures, Logic Flow, External Dependencies, Complexity
    technical_report_json = Column(Text) 
    
    # --- Metrics ---
    complexity_rating = Column(String) # Medium, High, Low
    modernization_tips = Column(Text)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


