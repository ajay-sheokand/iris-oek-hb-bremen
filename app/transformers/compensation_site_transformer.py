from shapely import make_valid
from shapely.geometry import MultiPolygon
from loguru import logger
import pandas as pd


STATE_CODE = "HB"
SOURCE_LAYER = "Kompensation_Flächen"


def _to_multipolygon(geom):
    if geom is None or geom.is_empty:
        return None
    if geom.geom_type == "MultiPolygon":
        return geom
    if geom.geom_type == "Polygon":
        return MultiPolygon([geom])
    if geom.geom_type == "GeometryCollection":
        parts = []
        for g in geom.geoms:
            if g.geom_type == "Polygon":
                parts.append(g)
            elif g.geom_type == "MultiPolygon":
                parts.extend(g.geoms)
        return MultiPolygon(parts) if parts else None
    return None


class CompensationSiteTransformer:
    def transform(self, gdf) -> tuple[list[dict], list[dict]]:
        records = []
        rejected = []
        repaired_count = 0

        for _, row in gdf.iterrows():
            geom = row.geometry

            if not geom.is_valid:
                geom = make_valid(geom)
                repaired_count += 1

            geom = _to_multipolygon(geom)
            if geom is None or geom.is_empty:
                rejected.append({
                    "site_id": row.site_id,
                    "reason": "geometry invalid and could not be repaired into a polygon",
                })
                continue

            responsible_entity = row.responsible_entity
            if responsible_entity == "kein Wert":
                responsible_entity = None

            records.append({
                "site_id": int(row.site_id),
                "state_code": STATE_CODE,
                "measure_code": f"{row.massnahme_praefix}-{row.massnahme_nr}",
                "description": row.description,
                "area_sqm": float(row.area_sqm),
                "compensation_status": row.compensation_status,
                "eco_pool_flag": bool(row.pool),
                "responsible_entity": responsible_entity,
                "municipality": row.municipality if pd.notna(row.municipality) else None,
                "geometry": geom,
                "source_layer": SOURCE_LAYER,
                "raw_attributes": row.raw_attributes,
            })

        logger.info(
            f"Transformed {len(records)} records ({repaired_count} geometries repaired), "
            f"{len(rejected)} rejected"
        )
        return records, rejected