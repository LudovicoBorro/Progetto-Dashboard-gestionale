from sqlmodel import Session, select, and_
from typing import List, Optional
import uuid
from data.models.project_resource import ProjectResource
from .base_repository import BaseRepository

class ProjectResourceRepository(BaseRepository[ProjectResource]):
    def __init__(self, session: Session):
        super().__init__(session, ProjectResource)

    def get_by_project(self, project_id: uuid.UUID) -> List[ProjectResource]:
        statement = select(ProjectResource).where(ProjectResource.project_id == project_id)
        return list(self.session.exec(statement).all())

    def get_by_project_and_name(self, project_id: uuid.UUID, name: str) -> Optional[ProjectResource]:
        statement = select(ProjectResource).where(
            and_(
                ProjectResource.project_id == project_id,
                ProjectResource.name == name
            )
        )
        return self.session.exec(statement).first()
