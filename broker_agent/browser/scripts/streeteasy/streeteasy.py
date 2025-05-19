from playwright._impl._errors import TargetClosedError
from playwright.async_api import Playwright

from broker_agent.browser.scraping_browser import ScrapingBrowser
from broker_agent.browser.scripts.streeteasy.streeteasy_listing import (
    process_streeteasy_listing,
)
from broker_agent.browser.scripts.streeteasy.streeteasy_search import (
    streeteasy_save_listings,
    streeteasy_search,
)
from broker_agent.common.enum import ApartmentType, WebsiteType
from broker_agent.common.exceptions import (
    PageNavigationLimitReached,
    ScraperAccessDenied,
)
from broker_agent.config.logging import get_logger
from broker_agent.config.settings import config
from database.connection import async_db_session

logger = get_logger(__name__)


async def get_streeteasy_listings(playwright: Playwright, user_agent: str) -> list[str]:
    """
    Helper to perform the search and return listing URLs from StreetEasy.
    """
    async with ScrapingBrowser(
        playwright, user_agent, scrape_images=False
    ) as search_page:
        await search_page.goto(WebsiteType.STREETEASY.value, timeout=60000)

        title = await search_page.title()
        if "denied" in title.lower():
            raise ScraperAccessDenied("Access denied to StreetEasy for [Search].")

        await streeteasy_search(
            search_page,
            min_price=config.streeteasy_min_price,
            max_price=config.streeteasy_max_price,
            apt_type=ApartmentType(config.streeteasy_apt_type),
        )

        listings = await streeteasy_save_listings(search_page)

        logger.info(f"Found {len(listings)} listings to process using [Search].")
        logger.debug(f"Listings from [Search]: {listings}")

    return listings


async def process_streeteasy_listings(
    playwright: Playwright,
    user_agent: str,
    listings: list[str],
) -> int:
    """
    Helper to process each listing URL in detail and save to DB.
    Returns the number of processed listings.
    """
    processed_count = 0
    try:
        async with async_db_session() as session:
            for i, listing_url in enumerate(listings):
                logger.info(f"Processing listing {i+1}/{len(listings)}: {listing_url}")
                try:
                    async with ScrapingBrowser(
                        playwright, user_agent, scrape_images=False
                    ) as listing_detail_page:
                        await process_streeteasy_listing(
                            listing_detail_page, listing_url, session
                        )
                        processed_count += 1
                except TargetClosedError as e:
                    logger.error(
                        f"Target closed while processing {listing_url}: {e}. "
                        f"Skipping this listing. {processed_count} listings processed so far."
                    )
                    continue
    except PageNavigationLimitReached:
        logger.warning(
            f"ScrapingBrowser encountered overall navigation limit. "
            f"Processed {processed_count} listings before stop."
        )
    return processed_count
