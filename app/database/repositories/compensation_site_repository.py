from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.compensation_site import CompensationSite
from app.database.repositories.base_repository import BaseRepository


class CompensationSiteRepository(BaseRepository[CompensationSite]):
    def __init__(self, session: Session):
        super().__init__(session, CompensationSite)

    def find_by_site_id(self, site_id: int, state_code: str) -> CompensationSite | None:
        statement = select(CompensationSite).where(
            CompensationSite.site_id == site_id,
            CompensationSite.state_code == state_code,
        )
        return self.session.scalars(statement).first()