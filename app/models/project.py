from pydantic import BaseModel
from typing import Optional

class UserAuth(BaseModel):
    username: str
    password: str

class ProjectConfig(BaseModel):
    llm_provider: str  # "Cloud" or "Local"
    interaction_lang: str # "English", "French", etc.
    speed_profile: str # "Turbo", "Fast", "Balanced", "Thorough"
    reasoning_effort: Optional[str] = "Medium"
    parallel_workers: Optional[int] = 5
