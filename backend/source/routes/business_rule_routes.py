from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from Config.llm_config import settings
from Persistence.sqlite.models import BusinessRule, Project, ProjectFile
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
        "business_purpose": rule.business_purpose or "",
        "functional_logic": rule.functional_logic or rule.business_logic or "",
        "technical_ref": technical_ref,
        "technical_yaml": technical_yaml or technical_ref,
        "filename": filename,
        "status": rule.status or "PENDING",
        "chunk_id": rule.chunk_id,
        "file_id": rule.file_id,
        "chunk_index": rule.chunk_index,
    }


def serialize_rules(db: Session, rules: list[BusinessRule]):
    file_ids = sorted({rule.file_id for rule in rules if rule.file_id})

    files = {}
    if file_ids:
        files = {
            file.id: file.filename
            for file in db.query(ProjectFile).filter(ProjectFile.id.in_(file_ids)).all()
        }

    return [
        serialize_rule(rule, files.get(rule.file_id, ""))
        for rule in rules
    ]


def project_ai_config(project: Project | None):
    if not project:
        return {
            "mode": "openrouter" if settings.OPENROUTER_API_KEY else "local",
            "provider": "openrouter" if settings.OPENROUTER_API_KEY else "local",
            "key": settings.OPENROUTER_API_KEY,
            "url": settings.OPENROUTER_BASE_URL,
            "model": settings.OPENROUTER_MODEL,
        }

    mode = project.ai_mode or project.llm_provider or "openrouter"

    return {
        "mode": mode,
        "provider": mode,
        "key": project.custom_api_key or settings.OPENROUTER_API_KEY,
        "url": project.custom_api_base_url or settings.OPENROUTER_BASE_URL,
        "model": project.llm_model or settings.OPENROUTER_MODEL,
    }


@router.post("/{run_id}/extract")
async def extract_rules(run_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter_by(run_id=run_id).first()

    config = project_ai_config(project)

    process = LogicExtractionProcess(
        db_session=db,
        llm_provider=config,
    )

    count = await process.extract_all_rules(run_id)

    rules = (
        db.query(BusinessRule)
        .filter_by(run_id=run_id)
        .order_by(BusinessRule.id)
        .all()
    )

    return {
        "status": "success",
        "run_id": run_id,
        "count": count,
        "rules": serialize_rules(db, rules),
    }


@router.get("/{run_id}")
async def get_rules(run_id: str, db: Session = Depends(get_db)):
    rules = (
        db.query(BusinessRule)
        .filter_by(run_id=run_id)
        .order_by(BusinessRule.id)
        .all()
    )

    return serialize_rules(db, rules)


@router.patch("/{rule_id}")
async def verify_rule(rule_id: int, data: dict, db: Session = Depends(get_db)):
    rule = db.query(BusinessRule).filter_by(id=rule_id).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    if "status" in data:
        rule.status = data["status"]

    new_text = data.get("text")
    if new_text is None:
        new_text = data.get("rule_text")

    if new_text is not None:
        rule.rule_text = new_text
        rule.business_logic = new_text

    if "business_purpose" in data:
        rule.business_purpose = data["business_purpose"]

    if "functional_logic" in data:
        rule.functional_logic = data["functional_logic"]
        rule.business_logic = data["functional_logic"] or rule.rule_text

    if "technical_ref" in data:
        rule.technical_ref = data["technical_ref"]

    db.commit()
    db.refresh(rule)

    filename = ""
    if rule.file_id:
        file = db.query(ProjectFile).filter_by(id=rule.file_id).first()
        filename = file.filename if file else ""

    return {
        "status": "success",
        "message": "Rule updated",
        "rule": serialize_rule(rule, filename),
    }