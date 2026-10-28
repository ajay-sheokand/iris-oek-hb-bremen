from sqlalchemy.orm import Session
from loguru import logger

from app.scrapers.bremen_oek.bremen_oek_scraper import BremenOekScraper
from app.parsers.bremen_oek_parser import BremenOekParser
from app.enrichers.municipality_enricher import MunicipalityEnricher
from app.transformers.compensation_site_transformer import CompensationSiteTransformer
from app.loaders.compensation_site_loader import CompensationSiteLoader


class LoadCompensationSitesCommand:
    def __init__(self, session: Session):
        self.session = session

    def execute(self) -> dict:
        logger.info("Starting Bremen compensation registry pipeline")

        gdb_path = BremenOekScraper().scrape()
        gdf = BremenOekParser().parse(gdb_path)
        gdf = MunicipalityEnricher().enrich(gdf)
        records, rejected = CompensationSiteTransformer().transform(gdf)

        load_stats = CompensationSiteLoader(self.session).load(records)

        summary = {
            "parsed": len(gdf),
            "transform_rejected": len(rejected),
            "transform_rejected_details": rejected,
            **load_stats,
        }
        logger.info(f"Pipeline complete: {summary}")
        return summary