from pathlib import Path

import pytest

from app.parsers.bremen_oek_parser import BremenOekParser

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_flaechen.gpkg"


@pytest.fixture
def parsed_gdf():
    return BremenOekParser().parse(FIXTURE_PATH)


def test_parses_all_fixture_rows(parsed_gdf):
    assert len(parsed_gdf) == 13


def test_renames_columns_to_internal_names(parsed_gdf):
    expected = {
        "site_id", "massnahme_praefix", "massnahme_nr", "description",
        "area_sqm", "pool", "compensation_status", "responsible_entity",
        "stand", "shape_length", "shape_area", "geometry", "raw_attributes",
    }
    assert expected.issubset(set(parsed_gdf.columns))


def test_raw_attributes_preserves_original_german_keys(parsed_gdf):
    row = parsed_gdf.iloc[0]
    assert "Fachobjekt_ID" in row["raw_attributes"]
    assert "MassnahmePraefix" in row["raw_attributes"]
    assert row["raw_attributes"]["Fachobjekt_ID"] == row["site_id"]


def test_raises_on_missing_expected_columns(tmp_path):
    import geopandas as gpd
    from shapely.geometry import Point

    bad_gdf = gpd.GeoDataFrame({"geometry": [Point(0, 0)]}, crs="EPSG:25832")
    bad_path = tmp_path / "bad.gpkg"
    bad_gdf.to_file(bad_path, layer="Kompensation_Flächen", driver="GPKG")

    with pytest.raises(ValueError):
        BremenOekParser().parse(bad_path)