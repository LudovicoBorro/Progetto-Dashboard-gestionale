from uuid import UUID
from sqlmodel import Session, select
from ..models.schedule_activity import ScheduleActivity
from .base_repository import BaseRepository

class ScheduleActivityRepository(BaseRepository[ScheduleActivity]):
    def __init__(self, session: Session):
        super().__init__(session, ScheduleActivity)

    def get_by_solution(self, solution_id: UUID) -> list[ScheduleActivity]:
        statement = select(ScheduleActivity).where(ScheduleActivity.solution_id == solution_id).order_by(ScheduleActivity.start_time.asc())
        try:
            result = self.session.exec(statement).all()
            return result
        except Exception as e:
            self.session.rollback()
            raise