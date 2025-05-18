from playwright.async_api import Page

from broker_agent.browser.scripts.streeteasy.streeteasy_listing import (
    save_listings_to_db,
    scrape_listing_details,
)
from broker_agent.browser.scripts.streeteasy.streeteasy_search import (
    streeteasy_save_listings,
    streeteasy_search,
)
from broker_agent.common.enum import ApartmentType, WebsiteType
from broker_agent.common.exceptions import ScraperAccessDenied
from broker_agent.config.logging import get_logger
from broker_agent.config.settings import config
from database.connection import async_db_session

logger = get_logger(__name__)


async def scrape_streeteasy(page: Page, error_message: str | None = None) -> None:
    await page.goto(WebsiteType.STREETEASY.value, timeout=60000)

    title = await page.title()
    if "denied" in title.lower():
        raise ScraperAccessDenied(f"Access denied to StreetEasy. Page title: {title}")

    await streeteasy_search(
        page,
        min_price=config.streeteasy_min_price,
        max_price=config.streeteasy_max_price,
        apt_type=ApartmentType(config.streeteasy_apt_type),
    )

    listings = await streeteasy_save_listings(page)

    logger.info(f"listings = {listings}")

    async with async_db_session() as session:
        for listing in listings:
            logger.info(f"scraping listing = {listing}")
            await page.goto(listing, timeout=60000)
            listing_details = await scrape_listing_details(page)
            listing_details["link"] = listing
            logger.info(f"listing_details = {listing_details}")
            await save_listings_to_db([listing_details], session)


async def scrape_apartments_dot_com(
    page: Page, error_message: str | None = None
) -> None:
    raise NotImplementedError("Apartments dotcom is not implemented")


async def scrape_renthop(page: Page, error_message: str | None = None) -> None:
    raise NotImplementedError("Renthop is not implemented")
