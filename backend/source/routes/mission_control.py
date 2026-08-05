from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from Persistence.sqlite.models import Project, ProjectFile
from Persistence.sqlite.session import get_db

router = APIRouter(prefix="/mission-control", tags=["Mission Control"])

_EVENT_LOG: deque[dict[str, Any]] = deque(maxlen=100)


def append_event(message: str, level: str = "info", project_id: str | None = None, details: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": message,
        "level": level,
        "project_id": project_id,
        "details": details or {},
    }
    _EVENT_LOG.append(payload)
    print(f"[mission-control] {payload['timestamp']} {level.upper()} {message}")
    return payload


@router.get("/status")
def get_status(db: Session = Depends(get_db)) -> dict[str, Any]:
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    files = db.query(ProjectFile).all()

    project_count = len(projects)
    files_count = len(files)
    active_project = projects[0] if projects else None

    progress = 0
    if project_count:
        progress = min(100, round((files_count / max(1, project_count * 5)) * 100))

    latest_event = _EVENT_LOG[-1] if _EVENT_LOG else None
    events = list(_EVENT_LOG)[-20:]

    return {
        "is_running": True,
        "progress": progress,
        "active_project": active_project.project_name if active_project else None,
        "project_count": project_count,
        "file_count": files_count,
        "latest_event": latest_event,
        "events": events,
        "active_chunk": f"#{min(files_count + 1, 99)} / {max(project_count, 1)}",
        "self_healing_events": max(0, len(events)),
        "tokens_used": "n/a",
    }


append_event("Mission Control connected", "info")
