import random

from playwright.async_api import Page, Playwright

from broker_agent.browser.scripts.apartments_dot_com import (
    get_apartments_dot_com_listings,
    process_apartments_dot_com_listings,
)
from broker_agent.browser.scripts.streeteasy.streeteasy import (
    get_streeteasy_listings,
    process_streeteasy_listings,
)
from broker_agent.config.logging import get_logger

logger = get_logger(__name__)

# NOTE: When using the remote hosted scraping browsers, only 1 initial navigation is allowed.
# Therefore, we need to spin up a new ScrapingBrowser for each listing URL.
# See https://docs.brightdata.com/scraping-automation/scraping-browser/configuration#single-navigation-per-session
# for more details.


async def scrape_streeteasy(
    playwright: Playwright,
    user_agent: str,
) -> None:
    """
    StreetEasy listings are building-based.
    """
    listing_urls = await get_streeteasy_listings(playwright, user_agent)

    if not listing_urls:
        logger.info("No listings found by [Search]. Skipping detail processing.")
        return

    random.shuffle(listing_urls)

    processed_count = await process_streeteasy_listings(
        playwright, user_agent, listing_urls
    )

    logger.info(
        f"Finished processing for StreetEasy. Processed {processed_count}/{len(listing_urls)} listings in detail."
    )


async def scrape_apartments_dot_com(
    playwright: Playwright,
    user_agent: str,
) -> None:
    """
    Apartments.com listings are building-based.
    """
    listing_urls = await get_apartments_dot_com_listings(playwright, user_agent)
    if not listing_urls:
        logger.info("No listings found by [Search]. Skipping detail processing.")
        return

    random.shuffle(listing_urls)

    processed_count = await process_apartments_dot_com_listings(
        playwright, user_agent, listing_urls
    )

    logger.info(
        f"Finished processing for Apartments.com. Processed {processed_count}/{len(listing_urls)} listings in detail."
    )


async def scrape_renthop(page: Page, error_message: str | None = None) -> None:
    """
    Renthop listings are building-based.
    """
    raise NotImplementedError("Renthop is not implemented")
