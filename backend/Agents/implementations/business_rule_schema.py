from typing import List, Optional

from pydantic import BaseModel, Field, ValidationError

class ExtractedBusinessRule(BaseModel):
    rule_text: str = Field(..., description="The business rule written as a user story")
    technical_ref: Optional[str] = Field(None, description="The specific COBOL line or YAML block")

class BusinessRuleList(BaseModel):
    rules: List[ExtractedBusinessRule]



def validate_rule_payload(decoded):
    if isinstance(decoded, list):
        decoded = {"rules": decoded}
    try:
        payload = BusinessRuleList.model_validate(decoded)
    except ValidationError:
        return []
    return [rule.model_dump() for rule in payload.rules]
