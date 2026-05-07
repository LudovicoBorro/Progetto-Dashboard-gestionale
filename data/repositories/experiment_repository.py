from uuid import UUID
from sqlmodel import Session, select
from ..models.experiment import Experiment
from .base_repository import BaseRepository

class ExperimentRepository(BaseRepository[Experiment]):
    def __init__(self, session: Session):
        super().__init__(session, Experiment)

    def get_by_project(self, project_id: UUID) -> list[Experiment]:
        statement = select(Experiment).where(Experiment.project_id == project_id).order_by(Experiment.created_at.desc())
        try:
            result = self.session.exec(statement).all()
            return result
        except Exception as e:
            self.session.rollback()
            raise