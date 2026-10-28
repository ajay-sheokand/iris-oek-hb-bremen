from pathlib import Path

import pytest

from app.parsers.bremen_oek_parser import BremenOekParser
from app.transformers.compensation_site_transformer import CompensationSiteTransformer

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_flaechen.gpkg"


@pytest.fixture
def transformed():
    gdf = BremenOekParser().parse(FIXTURE_PATH)
    gdf["municipality"] = None  # enrichment is tested separately; not needed here
    return CompensationSiteTransformer().transform(gdf)


def test_all_records_have_valid_multipolygon_geometry(transformed):
    records, rejected = transformed
    for record in records:
        assert record["geometry"].geom_type == "MultiPolygon"
        assert record["geometry"].is_valid


def test_repairs_known_invalid_geometries(transformed):
    records, rejected = transformed
    repaired_ids = {926, 1339}  # the two invalid-geometry sites in the fixture
    record_ids = {r["site_id"] for r in records}
    assert repaired_ids.issubset(record_ids)


def test_normalizes_kein_wert_to_none(transformed):
    records, rejected = transformed
    kein_wert_records = [r for r in records if r["site_id"] in (235, 236)]
    assert kein_wert_records
    assert all(r["responsible_entity"] is None for r in kein_wert_records)


def test_eco_pool_flag_is_boolean(transformed):
    records, rejected = transformed
    pool_records = [r for r in records if r["site_id"] in (431, 552)]
    assert all(r["eco_pool_flag"] is True for r in pool_records)
    assert all(isinstance(r["eco_pool_flag"], bool) for r in records)


def test_measure_code_is_built_from_praefix_and_nr(transformed):
    records, rejected = transformed
    record = next(r for r in records if r["site_id"] == 958)
    assert "-" in record["measure_code"]