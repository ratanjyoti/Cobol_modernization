import requests

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


def _openrouter_error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text[:500] or response.reason

    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        return str(error.get("message") or error.get("code") or payload)[:500]
    if error:
        return str(error)[:500]
    return str(payload)[:500]


def validate_cloud_chat_config(config: dict):
    mode = (config.get("mode") or config.get("provider") or "local").lower()
    if mode not in {"openrouter", "api", "custom", "cloud"}:
        return

    api_key = config.get("key")
    base_url = (config.get("url") or settings.OPENROUTER_BASE_URL).rstrip("/")
    model = config.get("model") or settings.OPENROUTER_MODEL

    if not api_key:
        raise HTTPException(
            status_code=400,
            detail=(
                "OpenRouter API key is missing on the backend. Save the key for this run, "
                "or set OPENROUTER_API_KEY on the backend host."
            ),
        )

    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://cobol-modernization-green.vercel.app",
                "X-Title": "ModernizerAI",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Reply OK only."}],
                "temperature": 0,
                "max_tokens": 8,
            },
            timeout=30,
        )
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=400,
            detail=f"OpenRouter validation request failed: {exc}",
        ) from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=400,
            detail=f"OpenRouter rejected model '{model}': {_openrouter_error_message(response)}",
        )

    try:
        content = response.json().get("choices", [{}])[0].get("message", {}).get("content")
    except Exception:
        content = None

    if not isinstance(content, str) or not content.strip():
        raise HTTPException(
            status_code=400,
            detail=(
                f"OpenRouter model '{model}' responded without chat text. "
                "Choose a text chat model, not an embedding, safety, or reasoning-only model."
            ),
        )


@router.post("/{run_id}/extract")
async def extract_rules(run_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter_by(run_id=run_id).first()

    config = project_ai_config(project)
    validate_cloud_chat_config(config)

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
