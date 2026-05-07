from uuid import uuid4, UUID
from enum import Enum
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column
from sqlalchemy.types import JSON
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .project import Project
    from .schedule import Schedule

class ProblemType(str, Enum):
    RCPSP = "RCPSP"
    RCPSP_MAX = "RCPSP_MAX"

class Method(str, Enum):
    EXACT = "exact"
    HEURISTIC_SINGLE_START = "heuristic_single_start"
    HEURISTIC_MULTI_START = "heuristic_multi_start"
    HEURISTIC_FALLBACK = "heuristic_fallback"

class Experiment(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="project.id", index=True, nullable=False, description="ID del progetto")
    problem_type: ProblemType = Field(index=True, nullable=False, description="Tipo di problema", default=ProblemType.RCPSP)
    method: Method = Field(index=True, nullable=False, description="Metodo utilizzato")
    num_runs: int = Field(index=True, nullable=False, description="Numero di runs", default=1)
    created_at: datetime = Field(index=True, default_factory=datetime.now, description="Data di creazione dell'esperimento")

    # Configuration
    experiment_config_json: Optional[dict] = Field(default=None, description="Configurazione utilizzata per l'esperimento", sa_column=Column(JSON))
    
    # Relationships
    project: "Project" = Relationship(back_populates="experiments")
    schedules: List["Schedule"] = Relationship(back_populates="experiment")