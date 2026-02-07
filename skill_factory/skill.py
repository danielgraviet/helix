from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional
from enum import Enum


class SkillStatus(str, Enum):
    BUILDING = "building"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"


class Skill(BaseModel):
    name: str
    description: str
    endpoint: str  # e.g. "http://localhost:9001/execute"
    port: int
    container_id: Optional[str] = None
    image_name: Optional[str] = None
    status: SkillStatus = SkillStatus.BUILDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SkillSpec(BaseModel):
    """Input to the Skill Factory — what Claude provides when creating a new skill."""
    name: str
    description: str
    execute_code: str  # the Python function body for the /execute handler
    view_post_code: str = "return HTMLResponse(_viewable_html)"  # handles form POST to /view
    dependencies: list[str] = Field(default_factory=list)  # extra pip packages needed
