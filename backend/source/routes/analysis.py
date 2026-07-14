from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from Persistence.sqlite.models import BusinessRule
from Persistence.sqlite.session import get_db

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.get("/business-rules/{run_id}")
async def get_business_rules(run_id: str, db: Session = Depends(get_db)):
    rules = db.query(BusinessRule).filter_by(run_id=run_id).order_by(BusinessRule.id).all()
    return {
        "rules": [
            {
                "id": rule.id,
                "rule_id": rule.rule_id,
                "cobol": rule.technical_ref or rule.technical_yaml,
                "english": rule.rule_text or rule.business_logic,
                "status": rule.status,
            }
            for rule in rules
        ]
    }


@router.patch("/confirm-rule/{rule_id}")
async def confirm_rule(rule_id: int, status: str, db: Session = Depends(get_db)):
    rule = db.query(BusinessRule).filter_by(id=rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule.status = status
    db.commit()
    return {"status": "Rule updated"}
