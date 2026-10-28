-- Reproducible example queries against iris_staging.compensation_sites,
-- run with: docker exec task-iris-postgis psql -U iris -d iris -f /path/to/this/file
-- (or paste each block into psql individually).

-- 1. Counts by processing outcome: compensation status, and whether a
--    municipality could be resolved during enrichment.
SELECT
    compensation_status,
    count(*) AS total,
    count(municipality) AS with_municipality,
    count(*) - count(municipality) AS without_municipality
FROM iris_staging.compensation_sites
GROUP BY compensation_status
ORDER BY total DESC;

-- 2. Spatial rollup: total compensation area (hectares) and site count per
--    municipality, for the sites a municipality could actually be resolved for.
SELECT
    municipality,
    count(*) AS site_count,
    round(sum(area_sqm) / 10000.0, 1) AS total_hectares
FROM iris_staging.compensation_sites
WHERE municipality IS NOT NULL
GROUP BY municipality
ORDER BY total_hectares DESC;

-- 3. Real spatial query: other compensation sites within 1km of site 235
--    ("östlich Stellfeldsweg"), using ST_DWithin / ST_Distance on the
--    stored MULTIPOLYGON geometry.
SELECT
    other.site_id,
    other.measure_code,
    other.municipality,
    round(ST_Distance(other.geometry, target.geometry)) AS distance_m
FROM iris_staging.compensation_sites AS other,
     (
         SELECT geometry
         FROM iris_staging.compensation_sites
         WHERE site_id = 235 AND state_code = 'HB'
     ) AS target
WHERE other.site_id != 235
  AND ST_DWithin(other.geometry, target.geometry, 1000)
ORDER BY distance_m;
