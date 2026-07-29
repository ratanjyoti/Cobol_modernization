from typing import List, Optional

from pydantic import BaseModel, Field, ValidationError


class ExtractedBusinessRule(BaseModel):
    rule_text: str = Field(..., description="Business intent rule that explains the outcome to preserve, not COBOL syntax")
    rule_type: Optional[str] = Field(None, description="Business rule category")
    technical_ref: Optional[str] = Field(None, description="The specific COBOL line or YAML block")
    confidence: Optional[str] = Field(None, description="Evidence confidence")


class BusinessRuleList(BaseModel):
    business_purpose: Optional[str] = None
    functional_logic: Optional[str] = None
    rules: List[ExtractedBusinessRule]



def validate_rule_payload(decoded):
    if isinstance(decoded, list):
        decoded = {"rules": decoded}
    try:
        payload = BusinessRuleList.model_validate(decoded)
    except ValidationError:
        return decoded
    return {
        "business_purpose": payload.business_purpose or "",
        "functional_logic": payload.functional_logic or "",
        "rules": [rule.model_dump() for rule in payload.rules],
    }
