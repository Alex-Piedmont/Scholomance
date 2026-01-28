"""Scrapers package for university tech transfer sites."""

from .base import BaseScraper, Technology, RetryConfig, retry_async
from .stanford import StanfordScraper
from .gatech import GatechScraper
from .uga import UGAScraper
from .mit import MITScraper
from .umich import UMichScraper
from .uf import UFScraper
from .jhu import JHUScraper
from .columbia import ColumbiaScraper
from .upenn import UPennScraper
from .harvard import HarvardScraper
from .utaustin import UTAustinScraper
from .ucsystem import UCSystemScraper
from .cornell import CornellScraper
from .cmu import CMUScraper
from .uiuc import UIUCScraper
from .techpub_base import TechPublisherScraper
from .warf import WARFScraper
from .uw import UWScraper
from .purdue import PurdueScraper
from .minnesota import MinnesotaScraper
from .northwestern import NorthwesternScraper
from .buffalo import BuffaloScraper
from .unlv import UNLVScraper
from .waynestate import WayneStateScraper
from .flintbox_base import FlintboxScraper
from .ucf import UCFScraper
from .colorado import ColoradoScraper
from .usc import USCScraper
from .usu import USUScraper
from .ttu import TTUScraper
from .uconn import UConnScraper
from .louisville import LouisvilleScraper
from .iowa import IowaScraper
from .rss_base import RSSBaseScraper
from .princeton import PrincetonScraper
from .michiganstate import MichiganStateScraper
from .texasstate import TexasStateScraper
from .duke import DukeScraper

# Registry of available scrapers
SCRAPERS = {
    "stanford": StanfordScraper,
    "gatech": GatechScraper,
    "uga": UGAScraper,
    "mit": MITScraper,
    "umich": UMichScraper,
    "uf": UFScraper,
    "jhu": JHUScraper,
    "columbia": ColumbiaScraper,
    "upenn": UPennScraper,
    "harvard": HarvardScraper,
    "utaustin": UTAustinScraper,
    "ucsystem": UCSystemScraper,
    "cornell": CornellScraper,
    "cmu": CMUScraper,
    "uiuc": UIUCScraper,
    "warf": WARFScraper,
    "uw": UWScraper,
    "purdue": PurdueScraper,
    "minnesota": MinnesotaScraper,
    "northwestern": NorthwesternScraper,
    "buffalo": BuffaloScraper,
    "unlv": UNLVScraper,
    "waynestate": WayneStateScraper,
    "ucf": UCFScraper,
    "colorado": ColoradoScraper,
    "usc": USCScraper,
    "usu": USUScraper,
    "ttu": TTUScraper,
    "uconn": UConnScraper,
    "louisville": LouisvilleScraper,
    "iowa": IowaScraper,
    "princeton": PrincetonScraper,
    "michiganstate": MichiganStateScraper,
    "texasstate": TexasStateScraper,
    "duke": DukeScraper,
}


def get_scraper(university_code: str) -> BaseScraper:
    """Get a scraper instance for the given university code."""
    if university_code not in SCRAPERS:
        raise ValueError(f"Unknown university: {university_code}. Available: {list(SCRAPERS.keys())}")
    return SCRAPERS[university_code]()


def list_scrapers() -> list[dict]:
    """List all available scrapers with their details."""
    result = []
    for code, scraper_class in SCRAPERS.items():
        scraper = scraper_class()
        result.append({
            "code": code,
            "name": scraper.name,
            "base_url": scraper.base_url,
        })
    return result


__all__ = [
    "BaseScraper",
    "Technology",
    "RetryConfig",
    "retry_async",
    "StanfordScraper",
    "GatechScraper",
    "UGAScraper",
    "MITScraper",
    "UMichScraper",
    "UFScraper",
    "JHUScraper",
    "ColumbiaScraper",
    "UPennScraper",
    "HarvardScraper",
    "UTAustinScraper",
    "UCSystemScraper",
    "CornellScraper",
    "CMUScraper",
    "UIUCScraper",
    "TechPublisherScraper",
    "WARFScraper",
    "UWScraper",
    "PurdueScraper",
    "MinnesotaScraper",
    "NorthwesternScraper",
    "BuffaloScraper",
    "UNLVScraper",
    "WayneStateScraper",
    "FlintboxScraper",
    "UCFScraper",
    "ColoradoScraper",
    "USCScraper",
    "USUScraper",
    "TTUScraper",
    "UConnScraper",
    "LouisvilleScraper",
    "IowaScraper",
    "RSSBaseScraper",
    "PrincetonScraper",
    "MichiganStateScraper",
    "TexasStateScraper",
    "DukeScraper",
    "SCRAPERS",
    "get_scraper",
    "list_scrapers",
]
