# Bremen Compensation Registry Harvester (IRIS-OEK-HB)

This repo pulls the Bremen's compensation site registry (Kompensationsverzeichnis) and loads it
into `iris_staging.compensation_sites`.

AI-assisted coding was used in this repo as well.

## Data source

The task spec points at a WFS endpoint, `https://geodatendienst.bremen.de/wfs/oekoflaechen`,
layer `hb_ausgleichsregister`. That endpoint doesn't resolve — no DNS record at all,
checked from two separate networks, not a one-off network issue on my end.

I went looking for the real source rather than treating this as a dead end. 

Bremen's
actual WFS host is `geodienste.bremen.de` (one letter different from what the spec
has), which I could confirm was live through its administrative boundaries service.


I tried the obvious layer-name guesses for the compensation data on that host
(`wfs_oekoflaechen`, `wfs_ausgleichsflaechen`, `wfs_kompensationsflaechen`, a few
more) — all 404. Looking at one of Bremen's actual working services showed why
guessing wasn't going to get anywhere: their WFS URLs use opaque random slugs
(the ALKIS parcel service, for example, is `wfs_hduk2958loah3976niun`), so there's
no naming pattern to find.


What did get me to the data was the regional metadata catalog at metaver.de, which
indexes published datasets for Bremen along with a few other states. Searching
"Ausgleichsflächen Bremen" there surfaced the actual registry: "Ausgleichsflächen
(Kompensationsverzeichnis) Land Bremen", the legally mandated registry under
§17(6) BNatSchG / §8(4) BremNatG. It's published three ways — a WMS (map tiles,
not queryable), an INSPIRE Atom feed, and a direct download: a ZIP containing an
Esri File Geodatabase, hosted at `gdi2.geo.bremen.de`. None of these are a WFS.


This harvester uses the direct ZIP/GDB download. It's real, current data (the file
was last updated 2026-06-24) and not a fixture, it's just not the WFS integration
pattern the spec describes, because that pattern doesn't actually exist for this
dataset. I kept the fetch logic isolated in its own scraper module specifically so
that if Bremen does ever stand up a real WFS for this, only that one module would
need to change.

Source data is CC-BY licensed, attribution to Landesamt GeoInformation Bremen.

## How it's structured

Same layering the rest of the IRIS codebase uses — scraper, parser, enricher,
transformer, loader, each one doing a single job, wired together by a command/runner
pair:

```
app/scrapers/bremen_oek/bremen_oek_scraper.py       downloads + unzips the GDB
app/parsers/bremen_oek_parser.py                    reads the layer, renames fields
app/enrichers/municipality_enricher.py              spatial join against boundary WFS
app/transformers/compensation_site_transformer.py   geometry repair, field cleanup
app/loaders/compensation_site_loader.py              upsert into Postgres
app/commands/load_compensation_sites_command.py     orchestrates the pipeline
app/runners/compensation_sites_runner.py            session handling
main.py                                              CLI entrypoint
```

## Scope: polygons only

The GDB actually has three layers — 829 polygons, 31 points, 128 lines. I only load
the polygon layer (`Kompensation_Flächen`). The spec describes polygons specifically,
and bringing in all three geometry types would mean a looser `GEOMETRY` column
instead of a proper `MULTIPOLYGON`. This was a deliberate scope decision, not
something I missed — points and lines could be added later behind the same
scraper/parser if it's ever needed.

## Field mapping

| Source (German) | Goes to | Notes |
|---|---|---|
| `Fachobjekt_ID` | `site_id` | unique in the layer; combined with `state_code` as the upsert key |
| `MassnahmePraefix` + `Massnahme_Nr` | `measure_code` | joined as `"{praefix}-{nr}"` |
| `Bezeichnung` | `description` | |
| `Flaechengroesse_qm` | `area_sqm` | checked against the GDB's own `SHAPE_Area`, matches closely |
| `Umsetzungsstatus` | `compensation_status` | left in German — 4 real categories, translating would lose precision |
| `Pool` | `eco_pool_flag` | cast to boolean |
| `Vorhabenstraeger` | `responsible_entity` | the `"kein Wert"` placeholder is normalized to `NULL` |
| — (derived) | `municipality` | see below, not present in the source |
| geometry | `geometry` | MULTIPOLYGON, EPSG:25832 — already the target CRS, no reprojection needed |
| everything, pre-rename | `raw_attributes` | kept as JSON for provenance |

## Municipality enrichment

Nothing in the source identifies which Stadtteil a site falls in, so I join each
site's centroid against Bremen's real boundary WFS (`wfs_verwaltungsgrenzen`, both
the Bremen and Bremerhaven Stadtteile layers).

I didn't use strict point-in-polygon containment for this. I checked it first with
a plain "within" join and got 656 matches out of 829, with 173 unmatched — a lot
more than expected, since only around 45 sites actually have a Lower-Saxony-prefixed
measure code (`Nds ...`). Looking into it, the compensation registry and the
boundary data are maintained independently and don't align perfectly at shared
edges — some sites were missing a match by only a few meters. Switching to
nearest-boundary-within-1000m fixed the edge cases: 741 matched, 88 unmatched.

Of those remaining 88, 33 are genuinely across the border in Lower Saxony, and the
other 55 carry a Bremen program code but sit more than a kilometer from any Bremen
or Bremerhaven boundary. I checked whether this was a Bremerhaven coverage gap,
since Bremen and Bremerhaven are two separate, non-contiguous parts of the same
state — but only 8 of those 55 have a Bremerhaven-related prefix, and the
boundaries I pulled do cover all of Bremerhaven's real districts. The more likely
explanation is that these are compensation measures registered under a Bremen
program but physically implemented on land outside Bremen's own territory, which
is apparently how ecological compensation banking often works. Either way, these
are left as `NULL` and counted, not guessed at or silently dropped.

## Known gaps

- The spec asks for cadastre names to be normalized alongside municipality. The
  source layer has no cadastre/Flurstück field at all — checked against the real
  GDB schema, not assumed — so there's nothing to normalize. `municipality` is
  the only location field derived, via the spatial join described above.
- 88 of 829 records have no municipality, for the reason above.
- `Stand` (the as-of date field) is empty for every single row in the source data.
  That's the source, not something lost in parsing.
- Points and lines layers aren't loaded, by design (see Scope above).
- There's no live WFS for this dataset at all. That's the one real deviation from
  what the spec describes, and it's unavoidable rather than a shortcut I took.

## Running it

```bash
cp .env.example .env
docker compose up -d postgres
uv run alembic upgrade head
docker compose up --build app
```

or `docker compose up --build` to bring up both services from nothing.

## Tests

```bash
docker compose up -d postgres
uv run pytest -v
```

10 tests: parsing (4), the transformer including geometry repair (5), and one
loader test that runs the load twice against a real Postgres instance and checks
the row count doesn't move on the second run.

## What an actual run looks like

```
parsed:                 829
geometries repaired:    6   (self-intersecting polygons, fixed with shapely's make_valid)
rejected at transform:  0
municipality matched:   741
municipality unmatched: 88
first load:              829 inserted, 0 updated, 0 failed
second load, same input: 0 inserted, 829 updated, 0 failed
```

Ran the full pipeline twice back to back and checked `count(*)` against
`count(distinct (site_id, state_code))` directly in Postgres — both come out to
829 either time. No duplicates from the second run.

## Sample queries

`sql/sample_queries.sql` has three reproducible queries against the loaded data:
counts by compensation status (with/without a resolved municipality), a spatial
rollup of total compensation area per municipality, and a real `ST_DWithin`
proximity query finding other sites within 1km of a given one. Run them with:

```bash
docker exec -i task-iris-postgis psql -U iris -d iris < sql/sample_queries.sql
```

The municipality rollup, for example, shows Fischereihafen with the most total
compensation area (1,062.8 ha across 36 sites) of any matched municipality.

## Assumptions

- `iris_staging` is created by this project's own Alembic migration. `iris_core`
  is never touched, as instructed.
- Used the plain (non-INSPIRE) GDB distribution rather than the INSPIRE-harmonized
  Atom feed version, since it covers both Bremen and Bremerhaven and keeps the
  original German field names instead of flattening everything into the generic
  EU schema.
