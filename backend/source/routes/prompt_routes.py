from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Query

from Agents.infrastructure.prompt_store import PromptStore


router = APIRouter(prefix="/prompts", tags=["Prompt Studio"])


class PromptUpdateRequest(BaseModel):
    content: str


@router.get("/code-generation")
def get_code_generation_prompts(project_id: str = Query(default="default")):
    store = PromptStore()

    return {
        "project_id": project_id,
        "prompts": store.list_prompts(project_id),
    }


@router.get("/code-generation/{prompt_key}")
def get_code_generation_prompt(
    prompt_key: str,
    project_id: str = Query(default="default"),
):
    store = PromptStore()

    try:
        return {
            "key": prompt_key,
            "project_id": project_id,
            "content": store.get_prompt(prompt_key, project_id),
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.put("/code-generation/{prompt_key}")
def update_code_generation_prompt(
    prompt_key: str,
    payload: PromptUpdateRequest,
    project_id: str = Query(default="default"),
):
    store = PromptStore()

    try:
        result = store.save_override(prompt_key, payload.content, project_id)
        return {
            "message": "Prompt override saved successfully.",
            **result,
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/code-generation/{prompt_key}/reset")
def reset_code_generation_prompt(
    prompt_key: str,
    project_id: str = Query(default="default"),
):
    store = PromptStore()

    try:
        result = store.reset_override(prompt_key, project_id)
        return {
            "message": "Prompt override reset successfully.",
            **result,
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))