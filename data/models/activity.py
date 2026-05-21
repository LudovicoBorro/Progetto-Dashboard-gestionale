from uuid import uuid4, UUID
from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel, Relationship
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .project import Project
    from .schedule_activity import ScheduleActivity

class Activity(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="project.id", index=True, nullable=False, description="ID del progetto", ondelete="CASCADE")
    id_for_project: int = Field(index=True, nullable=False, description="ID dell'attività all'interno del progetto (es. 0, 1, 2...)", ge=0)
    name: str = Field(index=True, nullable=False, description="Nome dell'attività")
    description: Optional[str] = Field(default=None, description="Descrizione dell'attività")
    
    # Store complex activity input (intervals, tuples, etc.)
    activity_config_json: Optional[dict] = Field(default=None, description="Dati di input specifici (es. durate stocastiche)", sa_column=Column(JSON))
    
    # Relationships
    project: "Project" = Relationship(back_populates="activities")
    schedule_activities: List["ScheduleActivity"] = Relationship(back_populates="activity", sa_relationship_kwargs={"cascade": "all, delete-orphan"})