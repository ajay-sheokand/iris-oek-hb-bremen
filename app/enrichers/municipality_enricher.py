from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from loguru import logger

WFS_BASE_URL = "https://geodienste.bremen.de/wfs_verwaltungsgrenzen"
BOUNDARY_LAYERS = ["app:Stadtteile_Bremen", "app:Stadtteile_Bremerhaven"]
MUNICIPALITY_FIELD = "bez_st"
MAX_SNAP_DISTANCE_M = 1000
CACHE_DIR = Path("data/raw/boundaries")


class MunicipalityEnricher:
    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._boundaries: gpd.GeoDataFrame | None = None

    def _fetch_layer(self, type_name: str) -> gpd.GeoDataFrame:
        cache_path = self.cache_dir / f"{type_name.replace(':', '_')}.gml"
        if not cache_path.exists():
            logger.info(f"Fetching boundary layer {type_name}")
            response = requests.get(
                WFS_BASE_URL,
                params={
                    "SERVICE": "WFS",
                    "VERSION": "2.0.0",
                    "REQUEST": "GetFeature",
                    "TYPENAMES": type_name,
                    "SRSNAME": "EPSG:25832",
                },
                timeout=60,
            )
            response.raise_for_status()
            cache_path.write_bytes(response.content)
        gdf = gpd.read_file(cache_path)
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:25832")
        return gdf

    def _load_boundaries(self) -> gpd.GeoDataFrame:
        if self._boundaries is None:
            layers = [self._fetch_layer(name) for name in BOUNDARY_LAYERS]
            combined = pd.concat(layers, ignore_index=True)
            boundaries = gpd.GeoDataFrame(combined, crs=layers[0].crs)
            boundaries = boundaries[[MUNICIPALITY_FIELD, "geometry"]].rename(
                columns={MUNICIPALITY_FIELD: "municipality"}
            )
            boundaries = boundaries.set_crs(layers[0].crs)
            self._boundaries = boundaries
        return self._boundaries

    def enrich(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        boundaries = self._load_boundaries()

        centroids = gdf.copy()
        centroids["geometry"] = gdf.geometry.centroid

        joined = gpd.sjoin_nearest(
            centroids,
            boundaries,
            how="left",
            max_distance=MAX_SNAP_DISTANCE_M,
            distance_col="_boundary_distance_m",
        )
        joined = joined[~joined.index.duplicated(keep="first")]

        result = gdf.copy()
        result["municipality"] = joined["municipality"]

        unmatched = result["municipality"].isna().sum()
        logger.info(
            f"Municipality enrichment: {len(result) - unmatched} matched (within {MAX_SNAP_DISTANCE_M}m), "
            f"{unmatched} unmatched (outside Bremen or no boundary within {MAX_SNAP_DISTANCE_M}m)"
        )
        return result