import shutil
import zipfile
from pathlib import Path

import requests
from loguru import logger

from app.config.data_sources import get_data_source

RAW_DIR = Path("data/raw/bremen_oek")
EXTRACT_DIR = Path("data/raw/bremen_oek_extracted")


class BremenOekScraper:
    def __init__(self, raw_dir: Path = RAW_DIR, extract_dir: Path = EXTRACT_DIR):
        self.raw_dir = raw_dir
        self.extract_dir = extract_dir
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.extract_dir.mkdir(parents=True, exist_ok=True)
        self.source = get_data_source("bremen_compensation_registry")

    def scrape(self) -> Path:
        zip_path = self.raw_dir / "Kompensationsverzeichnis_HB_BHV.zip"
        try:
            self._download(self.source.urls[0], zip_path)
        except Exception as exc:
            if zip_path.exists():
                logger.warning(f"Download failed ({exc}), falling back to cached file: {zip_path}")
            else:
                raise RuntimeError(f"Download failed and no cached file exists: {exc}") from exc

        return self._extract(zip_path)

    def _download(self, url: str, dest: Path) -> None:
        logger.info(f"Downloading {url}")
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        dest.write_bytes(response.content)
        logger.info(f"Saved {len(response.content)} bytes to {dest}")

    def _extract(self, zip_path: Path) -> Path:
        if self.extract_dir.exists():
            shutil.rmtree(self.extract_dir)
        self.extract_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(self.extract_dir)

        gdb_dirs = list(self.extract_dir.rglob("*.gdb"))
        if not gdb_dirs:
            raise RuntimeError(f"No .gdb directory found after extracting {zip_path}")
        return gdb_dirs[0]