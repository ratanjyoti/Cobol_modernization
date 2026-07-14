from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from Config.llm_config import settings
from Persistence.sqlite.models import BusinessRule, ProjectFile
from Persistence.sqlite.session import get_db
from Processes.logic_extraction_process import LogicExtractionProcess

router = APIRouter(prefix="/business-rules", tags=["Business Logic"])


def serialize_rule(rule: BusinessRule, filename: str = ""):
    technical_yaml = rule.technical_yaml or ""
    technical_ref = rule.technical_ref or technical_yaml or ""
    return {
        "id": rule.id,
        "rule_id": rule.rule_id,
        "rule_text": rule.rule_text or rule.business_logic or "",
        "technical_ref": technical_ref,
        "technical_yaml": technical_yaml or technical_ref,
        "filename": filename,
        "status": rule.status or "PENDING",
    }


def serialize_rules(db: Session, rules: list[BusinessRule]):
    file_ids = sorted({rule.file_id for rule in rules if rule.file_id})
    files = {}
    if file_ids:
        files = {
            file.id: file.filename
            for file in db.query(ProjectFile).filter(ProjectFile.id.in_(file_ids)).all()
        }
    return [serialize_rule(rule, files.get(rule.file_id, "")) for rule in rules]


@router.post("/{run_id}/extract")
async def extract_rules(run_id: str, db: Session = Depends(get_db)):
    provider = "openrouter" if settings.OPENROUTER_API_KEY else "local"
    process = LogicExtractionProcess(db, llm_provider=provider)
    await process.extract_all_rules(run_id)
    rules = db.query(BusinessRule).filter_by(run_id=run_id).order_by(BusinessRule.id).all()
    return serialize_rules(db, rules)


@router.get("/{run_id}")
async def get_rules(run_id: str, db: Session = Depends(get_db)):
    rules = db.query(BusinessRule).filter_by(run_id=run_id).order_by(BusinessRule.id).all()
    return serialize_rules(db, rules)


@router.patch("/{rule_id}")
async def verify_rule(rule_id: int, data: dict, db: Session = Depends(get_db)):
    rule = db.query(BusinessRule).filter_by(id=rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule.status = data.get("status", rule.status)
    if "text" in data:
        rule.rule_text = data["text"]
        rule.business_logic = data["text"]

    db.commit()
    db.refresh(rule)
    filename = ""
    if rule.file_id:
        file = db.query(ProjectFile).filter_by(id=rule.file_id).first()
        filename = file.filename if file else ""
    return {"status": "success", "message": "Rule updated", "rule": serialize_rule(rule, filename)}
