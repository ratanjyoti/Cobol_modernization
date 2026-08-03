import json
from pathlib import Path

import requests

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from Config.llm_config import settings
from Persistence.sqlite.models import BusinessRule, Project, ProjectFile
from Persistence.sqlite.session import get_db
from Processes.logic_extraction_process import LogicExtractionProcess
from Processes.procedural_flow_process import ProceduralFlowProcess
from services.migration_scope_service import MigrationScopeService

router = APIRouter(prefix="/business-rules", tags=["Business Logic"]) 

"""API layer between the frontend, business-rule extraction process, LLM configuration, and SQLite storage."""

def serialize_rule(rule: BusinessRule, filename: str = "", metadata: dict | None = None):
    metadata = metadata or {}
    technical_yaml = rule.technical_yaml or ""
    technical_ref = rule.technical_ref or technical_yaml or ""
    rule_text = rule.rule_text or rule.business_logic or ""
    business_purpose = rule.business_purpose or (
        f"Stored business rules were extracted from {filename or 'the uploaded source file'}."
        if rule_text else ""
    )
    functional_logic = rule.functional_logic or rule.business_logic or (
        f"Review the stored rule text and technical evidence for this extracted rule. {technical_ref}".strip()
        if rule_text else ""
    )

    return {
        "id": rule.id,
        "rule_id": rule.rule_id,
        "rule_text": rule_text,
        "business_purpose": business_purpose,
        "functional_logic": functional_logic,
        "technical_ref": technical_ref,
        "technical_yaml": technical_yaml or technical_ref,
        "filename": filename,
        "detected_language": metadata.get("detected_language", ""),
        "agent_name": metadata.get("agent_name", ""),
        "agent_key": metadata.get("agent_key", ""),
        "fallback_used": bool(metadata.get("fallback_used", False)),
        "fallback_reason": metadata.get("fallback_reason", ""),
        "business_rules_count": metadata.get("business_rules_count", 0),
        "status": rule.status or "PENDING",
        "chunk_id": rule.chunk_id,
        "file_id": rule.file_id,
        "chunk_index": rule.chunk_index,
    }


def _business_logic_metadata(db: Session, run_id: str) -> dict[int, dict]:
    try:
        summary_path = (
            Path(__file__).resolve().parents[2]
            / "output"
            / "business_logic"
            / run_id
            / "summary.json"
        )
        summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {"results": []}
    except Exception:
        summary = {"results": []}

    metadata = {}
    for item in summary.get("results") or []:
        if not isinstance(item, dict):
            continue
        file_id = item.get("file_id")
        if file_id is None:
            continue
        try:
            metadata[int(file_id)] = item
        except Exception:
            continue
    if metadata:
        return metadata

    count_rows = (
        db.query(BusinessRule.file_id, func.count(BusinessRule.id))
        .filter(BusinessRule.run_id == run_id, BusinessRule.file_id.isnot(None))
        .group_by(BusinessRule.file_id)
        .all()
    )
    counts = {int(file_id): int(count) for file_id, count in count_rows if file_id is not None}
    if not counts:
        return metadata

    files = (
        db.query(ProjectFile)
        .filter(ProjectFile.run_id == run_id, ProjectFile.id.in_(counts.keys()))
        .all()
    )

    for project_file in files:
        language = (
            getattr(project_file, "detected_language", None)
            or getattr(project_file, "detected_lang", None)
            or getattr(project_file, "language", None)
            or "unknown"
        )
        agent_name = _business_agent_name(language)
        metadata[int(project_file.id)] = {
            "file_id": project_file.id,
            "file_name": project_file.filename,
            "detected_language": language,
            "agent_name": agent_name,
            "agent_key": agent_name.replace("BusinessLogicAgent", "").lower() or "generic",
            "fallback_used": False,
            "fallback_reason": "",
            "business_rules_count": counts.get(int(project_file.id), 0),
        }

    return metadata


def _business_agent_name(language: str) -> str:
    normalized = str(language or "").lower().strip()
    if normalized.startswith("cobol"):
        return "CobolBusinessLogicAgent"
    if normalized.startswith("telon"):
        return "TelonBusinessLogicAgent"
    if normalized in {"jcl", "job control language"}:
        return "JclBusinessLogicAgent"
    if normalized in {"copybook", "cpy"}:
        return "CopybookBusinessLogicAgent"
    if normalized in {"sql", "db2"}:
        return "SqlBusinessLogicAgent"
    return "GenericBusinessLogicAgent"


def serialize_rules(db: Session, rules: list[BusinessRule], run_id: str = ""):
    file_ids = sorted({rule.file_id for rule in rules if rule.file_id})

    files = {}
    if file_ids:
        files = {
            file.id: file.filename
            for file in db.query(ProjectFile).filter(ProjectFile.id.in_(file_ids)).all()
        }

    metadata = _business_logic_metadata(db, run_id) if run_id else {}

    return [
        serialize_rule(rule, files.get(rule.file_id, ""), metadata.get(rule.file_id, {}))
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
            detail="Please add your OpenRouter API key in AI Configuration.",
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


def _require_stage_allowed(db: Session, run_id: str, stage: str):
    project = db.query(Project).filter(Project.run_id == run_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    service = MigrationScopeService()
    scope = service.get_scope(getattr(project, "migration_scope", None))
    if not service.is_stage_allowed(scope.id, stage):
        raise HTTPException(
            status_code=403,
            detail=(
                f"{stage} is not allowed for selected scope {scope.title}. "
                "Upgrade migration scope to run this stage."
            ),
        )


@router.post("/{run_id}/extract")
async def extract_rules(run_id: str, db: Session = Depends(get_db)):
    _require_stage_allowed(db, run_id, MigrationScopeService.STAGE_BUSINESS_LOGIC)
    project = db.query(Project).filter_by(run_id=run_id).first()

    config = project_ai_config(project)
    validate_cloud_chat_config(config)

    process = LogicExtractionProcess(
        db_session=db,
        llm_provider=config,
    )

    summary = await process.extract_all_rules(run_id)

    rules = (
        db.query(BusinessRule)
        .filter_by(run_id=run_id)
        .order_by(BusinessRule.id)
        .all()
    )

    return {
        "status": "success",
        "run_id": run_id,
        "count": len(rules),
        "extraction_summary": summary,
        "results": summary.get("results", []),
        "rules": serialize_rules(db, rules, run_id),
    }


@router.get("/{run_id}")
async def get_rules(run_id: str, db: Session = Depends(get_db)):
    rules = (
        db.query(BusinessRule)
        .filter_by(run_id=run_id)
        .order_by(BusinessRule.id)
        .all()
    )

    return serialize_rules(db, rules, run_id)


@router.post("/{run_id}/procedural-flow/extract")
async def extract_procedural_flow(run_id: str, db: Session = Depends(get_db)):
    _require_stage_allowed(db, run_id, MigrationScopeService.STAGE_PROCEDURAL_FLOW)
    try:
        process = ProceduralFlowProcess(db)
        return process.extract_all(run_id=run_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{run_id}/procedural-flow")
async def list_procedural_flows(run_id: str, db: Session = Depends(get_db)):
    try:
        process = ProceduralFlowProcess(db)
        return process.list_flows(run_id=run_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{run_id}/procedural-flow/{file_id}")
async def get_procedural_flow(run_id: str, file_id: str, db: Session = Depends(get_db)):
    try:
        process = ProceduralFlowProcess(db)
        return process.get_flow(run_id=run_id, file_id=file_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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
