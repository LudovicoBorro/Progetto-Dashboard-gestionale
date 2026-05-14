from typing import Generic, TypeVar, Type, List, Optional
from uuid import UUID
from sqlmodel import Session, select, SQLModel

T = TypeVar("T", bound=SQLModel)

class BaseRepository(Generic[T]):
    """
    Classe base per i repository che contiene i metodi base per interagire con il DB.
    Implementa le operazioni CRUD. Tutti gli altri repository ereditano da questa classe.
    """
    def __init__(self, session: Session, model: Type[T]):
        self.session = session
        self.model = model

    def get_by_id(self, id: UUID) -> Optional[T]:
        try:
            return self.session.get(self.model, id)
        except Exception as e:
            self.session.rollback()
            raise

    def get_all(self) -> List[T]:
        statement = select(self.model)
        try:
            return self.session.exec(statement).all()
        except Exception as e:
            self.session.rollback()
            raise

    def create(self, entity: T) -> T:
        try:
            self.session.add(entity)
            self.session.commit()
            self.session.refresh(entity)
            return entity
        except Exception as e:
            self.session.rollback()
            raise

    def update(self, entity: T) -> T:
        try:
            self.session.add(entity)
            self.session.commit()
            self.session.refresh(entity)
            return entity
        except Exception as e:
            self.session.rollback()
            raise

    def delete(self, id: UUID) -> bool:
        try:
            entity = self.get_by_id(id)
            if entity:
                self.session.delete(entity)
                self.session.commit()
                return True
            return False
        except Exception as e:
            self.session.rollback()
            raise
