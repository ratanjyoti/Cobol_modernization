from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SourceLanguage(str, Enum):
    COBOL = "cobol"
    TELON = "telon"
    JCL = "jcl"
    UNKNOWN = "unknown"


class TargetLanguage(str, Enum):
    JAVA = "java"
    PYTHON = "python"
    CSHARP = "csharp"


class TargetFramework(str, Enum):
    QUARKUS = "quarkus"
    FASTAPI = "fastapi"
    ASPNET = "aspnet"


class CodeGenerationStatus(str, Enum):
    PENDING = "PENDING"
    PLANNING = "PLANNING"
    PLANNED = "PLANNED"
    GENERATING = "GENERATING"
    GENERATED = "GENERATED"
    FAILED = "FAILED"


class GeneratedFileType(str, Enum):
    RESOURCE = "resource"
    CONTROLLER = "controller"
    ROUTER = "router"
    SERVICE = "service"
    REPOSITORY = "repository"
    DTO = "dto"
    DOMAIN = "domain"
    EXCEPTION = "exception"
    CONFIG = "config"
    TEST = "test"
    README = "readme"
    OTHER = "other"


class TargetProfile(BaseModel):
    id: str
    target_language: TargetLanguage
    framework: str
    constitution_text: str
    raw_profile: Dict[str, Any] = Field(default_factory=dict)


class BusinessRuleContext(BaseModel):
    rule_id: Optional[str] = ""
    rule_text: str = ""
    business_purpose: str = ""
    functional_logic: str = ""
    technical_ref: str = ""


class DependencyContext(BaseModel):
    source_file: str = ""
    target_item: str = ""
    relation_type: str = ""
    context: str = ""
    resolved: bool = True


class ChunkCodegenContext(BaseModel):
    chunk_id: int
    file_id: int
    chunk_index: int
    filename: str
    filepath: str
    source_language: SourceLanguage = SourceLanguage.UNKNOWN
    raw_code: str
    technical_yaml: str = ""
    business_rules: List[BusinessRuleContext] = Field(default_factory=list)
    dependencies: List[DependencyContext] = Field(default_factory=list)
    context_packet: Dict[str, Any] = Field(default_factory=dict)


class PlannedClass(BaseModel):
    class_name: str
    file_path: str
    layer: str
    responsibility: str
    source_mapping: List[str] = Field(default_factory=list)


class PlannedMethod(BaseModel):
    method_name: str
    owning_class: str
    responsibility: str
    source_mapping: List[str] = Field(default_factory=list)
    inputs: List[str] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=list)


class ConversionPlan(BaseModel):
    run_id: str
    file_id: int
    source_file: str
    source_language: SourceLanguage
    target_language: TargetLanguage
    target_framework: str
    target_package_or_namespace: str = ""
    summary: str = ""
    classes: List[PlannedClass] = Field(default_factory=list)
    methods: List[PlannedMethod] = Field(default_factory=list)
    data_models: List[Dict[str, Any]] = Field(default_factory=list)
    external_dependencies: List[str] = Field(default_factory=list)
    unresolved_items: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    raw_plan: Dict[str, Any] = Field(default_factory=dict)


class GeneratedFile(BaseModel):
    path: str
    language: TargetLanguage
    file_type: GeneratedFileType = GeneratedFileType.OTHER
    content: str
    source_file: Optional[str] = ""
    notes: List[str] = Field(default_factory=list)


class CodeGenerationResult(BaseModel):
    run_id: str
    target_language: TargetLanguage
    target_framework: str
    status: CodeGenerationStatus
    summary: str = ""
    generated_files: List[GeneratedFile] = Field(default_factory=list)
    unresolved_items: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class FileCodegenContext(BaseModel):
    run_id: str
    file_id: int
    filename: str
    filepath: str = ""
    source_language: SourceLanguage = SourceLanguage.UNKNOWN
    raw_code: str = ""
    technical_yaml: str = ""
    business_rules: List[BusinessRuleContext] = Field(default_factory=list)
    dependencies: List[DependencyContext] = Field(default_factory=list)
    chunks: List[ChunkCodegenContext] = Field(default_factory=list)


def model_to_dict(model: BaseModel) -> Dict[str, Any]:
    """
    Pydantic v1/v2 compatible dict conversion.
    """
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()
