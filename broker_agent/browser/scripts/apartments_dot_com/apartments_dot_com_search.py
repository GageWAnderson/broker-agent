from playwright.async_api import Page

from broker_agent.common.utils import random_human_delay
from broker_agent.config.logging import get_logger

logger = get_logger(__name__)


async def get_apartments_dot_com_listings(
    page: Page,
) -> list[str]:
    """
    Scrapes listing URLs from the currently loaded apartments.com search results page.
    """
    logger.info("Scraping listings from the current page...")
    listings_selector = "article.placard"
    logger.info(f"Waiting for listings to appear with selector: '{listings_selector}'")
    try:
        await page.wait_for_selector(listings_selector, timeout=30000)
    except Exception:
        logger.warning(
            "No listings found on this page, or page timed out. Returning empty list."
        )
        return []

    await random_human_delay()

    listing_elements = await page.query_selector_all(listings_selector)

    page_urls = []
    for element in listing_elements:
        url = await element.get_attribute("data-url")
        if url:
            page_urls.append(url)
        await random_human_delay(50, 250)

    if not page_urls:
        logger.info("No URLs found on the current page.")
    else:
        logger.info(f"Found {len(page_urls)} listings on the page.")

    return page_urls
