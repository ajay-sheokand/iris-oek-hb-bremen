from dataclasses import dataclass

@dataclass(frozen=True)
class DataSource:
    name: str
    country_code: str
    urls: tuple[str, ...]
    enabled: bool = True



DATA_SOURCES = {
    "bremen_compensation_registry": DataSource(
        name="bremen_compensation_registry",
        country_code="DE",
        urls=(
            "https://gdi2.geo.bremen.de/inspire/download/Kompensationsverzeichnis/data/Kompensationsverzeichnis_HB_BHV.zip",
        ),
    ),
}


def get_data_source(name:str) -> DataSource:
    source = DATA_SOURCES.get(name)
    if source is None or not source.enabled:
        raise ValueError(f"Data source '{name}' is not available or not enabled.")
    return source