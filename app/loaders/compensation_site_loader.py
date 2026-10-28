from sqlalchemy.orm import Session
from loguru import logger
from geoalchemy2.shape import from_shape

from app.database.repositories.compensation_site_repository import CompensationSiteRepository

UPDATABLE_FIELDS = [
    "measure_code", "description", "area_sqm", "compensation_status",
    "eco_pool_flag", "responsible_entity", "municipality", "geometry",
    "source_layer", "raw_attributes",
]


class CompensationSiteLoader:
    def __init__(self, session: Session):
        self.session = session
        self.repository = CompensationSiteRepository(session)

    def load(self, records: list[dict]) -> dict:
        inserted = 0
        updated = 0
        failed = 0
        failures = []

        for record in records:
            try:
                payload = {**record, "geometry": from_shape(record["geometry"], srid=25832)}
                with self.session.begin_nested():
                    existing = self.repository.find_by_site_id(
                        payload["site_id"], payload["state_code"]
                    )
                    if existing:
                        for field in UPDATABLE_FIELDS:
                            setattr(existing, field, payload[field])
                        updated += 1
                    else:
                        self.repository.create(**payload)
                        inserted += 1
            except Exception as exc:
                failed += 1
                failures.append({"site_id": record.get("site_id"), "error": str(exc)})
                logger.warning(f"Failed to load site_id={record.get('site_id')}: {exc}")
        self.session.commit()

        stats = {
            "processed": len(records),
            "inserted": inserted,
            "updated": updated,
            "failed": failed,
            "failures": failures,
        }
        logger.info(f"Load complete: {stats}")
        return stats