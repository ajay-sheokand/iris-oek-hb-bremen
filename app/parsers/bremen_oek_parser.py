from pathlib import Path

import geopandas as gpd
from loguru import logger

LAYER_NAME = "Kompensation_Flächen"

COLUMN_MAP = {
    "Fachobjekt_ID": "site_id",
    "MassnahmePraefix": "massnahme_praefix",
    "Massnahme_Nr": "massnahme_nr",
    "Bezeichnung": "description",
    "Flaechengroesse_qm": "area_sqm",
    "Pool": "pool",
    "Umsetzungsstatus": "compensation_status",
    "Vorhabenstraeger": "responsible_entity",
    "Stand": "stand",
    "SHAPE_Length": "shape_length",
    "SHAPE_Area": "shape_area",
}


class BremenOekParser:
    def parse(self, gdb_path: Path) -> gpd.GeoDataFrame:
        logger.info(f"Reading layer '{LAYER_NAME}' from {gdb_path}")
        gdf = gpd.read_file(gdb_path, layer=LAYER_NAME)

        missing = set(COLUMN_MAP) - set(gdf.columns)
        if missing:
            raise ValueError(f"Expected columns missing from source layer: {missing}")

        gdf["raw_attributes"] = gdf.drop(columns="geometry").to_dict(orient="records")
        gdf = gdf.rename(columns=COLUMN_MAP)

        logger.info(f"Parsed {len(gdf)} features from {LAYER_NAME}")
        return gdf