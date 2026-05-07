from uuid import UUID
from sqlmodel import Session, select
from ..models.activity import Activity
from .base_repository import BaseRepository

class ActivityRepository(BaseRepository[Activity]):
    def __init__(self, session: Session):
        super().__init__(session, Activity)

    def get_by_project(self, project_id: UUID) -> list[Activity]:
        statement = select(Activity).where(Activity.project_id == project_id)
        try:
            result = self.session.exec(statement).all()
            return result
        except Exception as e:
            self.session.rollback()
            raise
