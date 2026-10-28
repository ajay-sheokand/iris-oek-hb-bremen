from pathlib import Path

import pytest
from sqlalchemy import text

from app.database.session import SessionLocal
from app.parsers.bremen_oek_parser import BremenOekParser
from app.transformers.compensation_site_transformer import CompensationSiteTransformer
from app.loaders.compensation_site_loader import CompensationSiteLoader

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_flaechen.gpkg"


@pytest.fixture
def clean_session():
    session = SessionLocal()
    session.execute(text("TRUNCATE iris_staging.compensation_sites RESTART IDENTITY"))
    session.commit()
    yield session
    session.execute(text("TRUNCATE iris_staging.compensation_sites RESTART IDENTITY"))
    session.commit()
    session.close()


@pytest.fixture
def fixture_records():
    gdf = BremenOekParser().parse(FIXTURE_PATH)
    gdf["municipality"] = None
    records, _ = CompensationSiteTransformer().transform(gdf)
    return records


def test_loading_twice_is_idempotent(clean_session, fixture_records):
    first = CompensationSiteLoader(clean_session).load(fixture_records)
    assert first["inserted"] == len(fixture_records)
    assert first["updated"] == 0
    assert first["failed"] == 0

    second = CompensationSiteLoader(clean_session).load(fixture_records)
    assert second["inserted"] == 0
    assert second["updated"] == len(fixture_records)
    assert second["failed"] == 0

    row_count = clean_session.execute(
        text("SELECT count(*) FROM iris_staging.compensation_sites")
    ).scalar()
    assert row_count == len(fixture_records)