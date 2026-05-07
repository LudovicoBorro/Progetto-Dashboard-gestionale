from uuid import uuid4, UUID
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column
from sqlalchemy.types import JSON
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .experiment import Experiment
    from .schedule_activity import ScheduleActivity

class Schedule(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    experiment_id: UUID = Field(foreign_key="experiment.id", index=True, nullable=False, description="ID dell'esperimento")
    makespan: Optional[int] = Field(index=True, nullable=True, description="Makespan della soluzione", ge=0)
    score: Optional[float] = Field(index=True, nullable=True, description="Score della soluzione (RCPSP_MAX)", ge=0)
    created_at: datetime = Field(index=True, default_factory=datetime.now, description="Data di creazione della soluzione")
    config_json: Optional[dict] = Field(default=None, description="Configurazione utilizzata per la soluzione", sa_column=Column(JSON))
    
    # Relationships
    experiment: "Experiment" = Relationship(back_populates="schedules")
    schedule_activities: List["ScheduleActivity"] = Relationship(back_populates="schedule")
