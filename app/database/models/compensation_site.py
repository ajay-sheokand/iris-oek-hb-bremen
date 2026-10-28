from sqlalchemy import String, Integer, Numeric, Boolean, UniqueConstraint, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2 import Geometry

from app.database.entity import BaseEntity


class CompensationSite(BaseEntity):
    __tablename__ = "compensation_sites"
    __table_args__ = (
        UniqueConstraint("site_id", "state_code", name="uq_compensation_site_state"),
        Index("ix_compensation_sites_status", "compensation_status"),
        Index("ix_compensation_sites_geometry", "geometry", postgresql_using="gist"),
        {"schema": "iris_staging"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    site_id: Mapped[int] = mapped_column(Integer, nullable=False)

    state_code: Mapped[str] = mapped_column(String(2), nullable=False)

    measure_code: Mapped[str] = mapped_column(String(50), nullable=False)

    description: Mapped[str | None] = mapped_column(String, nullable=True)

    area_sqm: Mapped[float] = mapped_column(Numeric, nullable=False)

    compensation_status: Mapped[str] = mapped_column(String(50), nullable=False)

    eco_pool_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    responsible_entity: Mapped[str | None] = mapped_column(String, nullable=True)

    municipality: Mapped[str | None] = mapped_column(String, nullable=True)

    geometry: Mapped[str] = mapped_column(Geometry(geometry_type="MULTIPOLYGON", srid=25832, spatial_index=False), nullable=False)

    source_layer: Mapped[str] = mapped_column(String, nullable=False)

    raw_attributes: Mapped[dict]= mapped_column(JSON, nullable = False)

