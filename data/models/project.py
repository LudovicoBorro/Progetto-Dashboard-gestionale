from uuid import uuid4, UUID
from datetime import datetime
from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel, Relationship
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .activity import Activity
    from .experiment import Experiment

class Project(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True, nullable=False, description="Nome del progetto", min_length=1)
    description: Optional[str] = Field(default=None, description="Descrizione del progetto")
    created_at: datetime = Field(index=True, default_factory=datetime.now, description="Data di creazione del progetto")
    last_edited_at: datetime = Field(default_factory=datetime.now, description="Data di aggiornamento del progetto")
    start_date: datetime = Field(default_factory=datetime.now, description="Data di inizio del progetto", index=True, nullable=False)
    end_date: datetime = Field(description="Data potenziale di fine progetto", index=True, nullable=False)
    status: Optional[str] = Field(default="Da schedulare", description="Stato del progetto") # Da schedulare, Completato, In esecuzione, Sospeso
    num_activities: int = Field(default=0, description="Numero di attività del progetto", nullable=False, ge=0, index=True)
    horizon_days: int = Field(default=0, description="Numero di giorni di orizzonte temporale del progetto", nullable=False, ge=0, index=True)
    initial_budget: float = Field(default=0, description="Budget iniziale del progetto", nullable=False, ge=0.0, index=True)
    final_budget: float = Field(default=0, description="Budget finale del progetto", nullable=False, ge=0.0, index=True)
    
    # Global project settings (e.g. booleans...)
    project_config_json: Optional[dict] = Field(default=None, description="Configurazioni globali del progetto", sa_column=Column(JSON))
    
    # Input_data snapshot
    input_data_json: Optional[dict] = Field(default=None, description="Snapshot input_data salvato dopo l'importazione da Excel", sa_column=Column(JSON))
    
    # Relationships
    activities: List["Activity"] = Relationship(back_populates="project")
    experiments: List["Experiment"] = Relationship(back_populates="project")