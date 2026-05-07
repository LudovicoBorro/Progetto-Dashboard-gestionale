from uuid import UUID
from sqlmodel import Session, select
from ..models.schedule import Schedule
from .base_repository import BaseRepository

class ScheduleRepository(BaseRepository[Schedule]):
    def __init__(self, session: Session):
        super().__init__(session, Schedule)

    def get_by_experiment(self, experiment_id: UUID) -> list[Schedule]:
        statement = select(Schedule).where(Schedule.experiment_id == experiment_id).order_by(Schedule.makespan.asc())
        try:
            result = self.session.exec(statement).all()
            return result
        except Exception as e:
            self.session.rollback()
            raise