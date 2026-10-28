from typing import Generic, TypeVar
from sqlalchemy import delete as sa_delete, func, select
from sqlalchemy.orm import Session

from app.database.base import Base

T = TypeVar("T", bound=Base)

class BaseRepository(Generic[T]):
    def __init__(self, session: Session, model: type[T]):
        self.session = session
        self.model = model

    # Create 
    def add(self, instance: T) -> T:
        self.session.add(instance)
        return instance

    def create(self, **kwargs) -> T:
        instance = self.model(**kwargs)
        self.session.add(instance)
        return instance

    def create_many(self, items: list[dict]) -> list[T]:
        instances = [self.model(**item) for item in items]
        self.session.add_all(instances)
        return instances

    def save(self, instance: T) -> T:
        self.session.add(instance)
        self.session.commit()
        self.session.refresh(instance)
        return instance

    def bulk_save(self, instances: list[T]) -> None:
        self.session.bulk_save_objects(instances)

    # --- Read ---
    def get_by_id(self, id_: int) -> T | None:
        return self.session.get(self.model, id_)

    def get_all(self) -> list[T]:
        return list(self.session.scalars(select(self.model)).all())

    def get_first(self) -> T | None:
        return self.session.scalars(select(self.model)).first()

    # --- Update ---
    def update(self, instance: T) -> T:
        return self.save(instance)

    # --- Delete ---
    def delete(self, instance: T) -> None:
        self.session.delete(instance)

    def delete_by_id(self, id_: int) -> bool:
        instance = self.get_by_id(id_)
        if instance is None:
            return False
        self.delete(instance)
        return True

    def delete_all(self) -> int:
        result = self.session.execute(sa_delete(self.model))
        return result.rowcount

    # --- Utilities ---
    def count(self) -> int:
        return self.session.scalar(select(func.count()).select_from(self.model))

    def exists_by_id(self, id_: int) -> bool:
        return self.get_by_id(id_) is not None

    # --- Session helpers ---
    def flush(self) -> None:
        self.session.flush()

    def refresh(self, instance: T) -> None:
        self.session.refresh(instance)

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    # --- Custom queries ---
    def execute(self, statement):
        return self.session.execute(statement)