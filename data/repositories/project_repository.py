from sqlmodel import Session, select
from ..models.project import Project
from .base_repository import BaseRepository
import uuid

class ProjectRepository(BaseRepository[Project]):
    """
    Repository dedicato ai Progetti per eseguire determinate 
    query al DB. Eredita i metodi base del BaseRepository.
    """
    def __init__(self, session: Session):
        super().__init__(session, Project)

    def get_by_name(self, name: str) -> list[Project]:
        statement = select(Project).where(Project.name == name)
        try:
            result = self.session.exec(statement).all()
            return result
        except Exception as e:
            self.session.rollback()
            raise

    def update_status(self, project_id: uuid.UUID, status: str):
        project = self.get_by_id(project_id)
        project.status = status
        return project