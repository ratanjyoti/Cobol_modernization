from pydantic import BaseModel, Field
from typing import List, Optional

class DataField(BaseModel):
    field_name: str = Field(..., description="The COBOL variable name, e.g., CUST-ID")
    data_type: str = Field(..., description="The PIC clause, e.g., PIC 9(8)")
    description: str = Field(..., description="What this field represents in business terms")

class DataStructure(BaseModel):
    structure_name: str = Field(..., description="The name of the record/group, e.g., CUSTOMER-RECORD")
    fields: List[DataField]

class LogicStep(BaseModel):
    step_number: int
    description: str = Field(..., description="Plain English description of what happens")
    technical_trigger: str = Field(..., description="The COBOL paragraph or statement that triggers this")

class TechnicalAnalysisReport(BaseModel):
    business_purpose: str = Field(..., description="High-level summary of what the program does")
    data_structures: List[DataStructure]
    logic_flow: List[LogicStep]
    dependencies: List[str] = Field(..., description="List of external files, programs, or copybooks")
    complexity_rating: str = Field(..., description="Low, Medium, or High")
    recommendations: List[str] = Field(..., description="Modernization advice for Java/Quarkus")
