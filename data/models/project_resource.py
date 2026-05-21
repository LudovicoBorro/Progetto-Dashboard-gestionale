import uuid
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from data.models.project import Project

class ProjectResource(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="project.id", index=True, nullable=False, ondelete="CASCADE")
    name: str = Field(index=True)
    capacity_min: int
    capacity_max: Optional[int] = Field(default=None)
    color_hex: Optional[str] = Field(default="#FFFFFF", nullable=False)

    project: "Project" = Relationship(back_populates="resources")