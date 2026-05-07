from uuid import uuid4, UUID
from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, TYPE_CHECKING
from pydantic import model_validator

if TYPE_CHECKING:
    from .schedule import Schedule
    from .activity import Activity

class ScheduleActivity(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    schedule_id: UUID = Field(foreign_key="schedule.id", index=True, nullable=False, description="ID dello schedule")
    activity_id: UUID = Field(foreign_key="activity.id", index=True, nullable=False, description="ID dell'attività")
    
    # Solver outputs (fixed values)
    start_time: int = Field(description="Tempo di inizio dell'attività", ge=0)
    end_time: int = Field(description="Tempo di fine dell'attività", ge=0)
    duration: int = Field(description="Durata effettiva assegnata", ge=0)
    resource_usage: Optional[dict] = Field(default={}, description="Risorse effettivamente assegnate", sa_column=Column(JSON))
    release_date: Optional[int] = Field(description="Data di rilascio dell'attività", ge=0)
    deadline: Optional[int] = Field(description="Data di scadenza dell'attività", ge=0)

    # Relationships
    schedule: "Schedule" = Relationship(back_populates="schedule_activities")
    activity: "Activity" = Relationship(back_populates="schedule_activities")

    @model_validator(mode="after")
    def validate_schedule_activity(self):
        if self.end_time < self.start_time:
            raise ValueError("end_time deve essere maggiore o uguale a start_time")
        if self.duration != self.end_time - self.start_time:
            raise ValueError("duration deve essere uguale a end_time - start_time")
        return self
