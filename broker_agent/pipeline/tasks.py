import random

from playwright.async_api import Page, Playwright

from broker_agent.browser.scraping_browser import ScrapingBrowser
from broker_agent.browser.scripts.apartments_dot_com import (
    get_apartments_dot_com_listings,
    process_apartments_dot_com_listings,
)
from broker_agent.browser.scripts.apartments_dot_com.utils import (
    advance_to_apartments_dot_com_start_page,
)
from broker_agent.browser.scripts.streeteasy.streeteasy import (
    get_streeteasy_listings,
    process_streeteasy_listings,
)
from broker_agent.common.enum import WebsiteType
from broker_agent.common.exceptions import ScraperAccessDenied
from broker_agent.common.utils import random_human_delay, run_with_retries
from broker_agent.config.logging import get_logger
from broker_agent.config.settings import config as broker_agent_config

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
    Apartments.com listings are building-based. This function orchestrates the scraping
    process by iterating through search result pages, extracting listing URLs from each
    page, and then processing those listings.

    Implements exponential backoff for retrying pagination navigation, using
    apartments_dot_com_max_retries, apartments_dot_com_base_delay, and apartments_dot_com_max_delay.
    """
    total_processed_count = 0
    total_urls_found = 0

    # Get exponential backoff config from settings, with defaults if not present
    max_retries = getattr(broker_agent_config, "apartments_dot_com_max_retries", 3)
    base_delay = getattr(broker_agent_config, "apartments_dot_com_base_delay", 2.0)
    max_delay = getattr(broker_agent_config, "apartments_dot_com_max_delay", 60.0)
    max_pages = getattr(broker_agent_config, "apartments_dot_com_max_pages", 10)
    start_page = getattr(broker_agent_config, "apartments_dot_com_start_page", 0)

    async with ScrapingBrowser(playwright, user_agent, scrape_images=False) as page:
        logger.info(f"Navigating to {WebsiteType.APARTMENTS_DOT_COM.value}")
        await page.goto(
            WebsiteType.APARTMENTS_DOT_COM.value,
            wait_until="domcontentloaded",
            timeout=60000,
        )

        await random_human_delay()

        title = await page.title()
        if "denied" in title.lower() or "robot" in title.lower():
            raise ScraperAccessDenied("Access denied to Apartments.com for [Search].")

        page_count = await advance_to_apartments_dot_com_start_page(
            page, start_page, max_retries, base_delay, max_delay
        )

        if page_count < start_page + 1:
            logger.info(f"Could not reach start page {start_page+1}. Stopping scrape.")
            return

        while page_count <= max_pages:
            logger.info(f"Processing page {page_count}...")
            listing_urls = await get_apartments_dot_com_listings(page)

            if not listing_urls:
                logger.info("No listings found on this page. Ending scrape.")
                break

            total_urls_found += len(listing_urls)
            random.shuffle(listing_urls)

            processed_count = await process_apartments_dot_com_listings(
                playwright, user_agent, listing_urls
            )
            total_processed_count += processed_count

            async def navigate_next_page() -> str:
                next_button_selector = "#paging .next"
                next_button = page.locator(next_button_selector).first
                if not await next_button.is_visible():
                    logger.info("No next page button found. Finished scraping.")
                    return "DONE"

                logger.info("Navigating to the next page.")
                await page.goto(
                    WebsiteType.APARTMENTS_DOT_COM.value,
                    wait_until="domcontentloaded",
                    timeout=60000,
                )
                await random_human_delay()
                await next_button.click()
                await random_human_delay(1500, 3500)
                return "OK"

            try:
                result = await run_with_retries(
                    action=navigate_next_page,
                    max_retries=max_retries,
                    base_delay=base_delay,
                    max_delay=max_delay,
                    logger=logger,
                    action_name="navigate to next page",
                )
                if result == "OK":
                    page_count += 1
                elif result == "DONE":
                    break
            except Exception:
                logger.error(
                    "Exceeded max retries for next page navigation. Stopping scrape."
                )
                break

    logger.info(
        f"Finished processing for Apartments.com. "
        f"Processed {total_processed_count}/{total_urls_found} listings in detail across {page_count - 1} page(s)."
    )


async def scrape_renthop(page: Page, error_message: str | None = None) -> None:
    """
    Renthop listings are building-based.
    """
    raise NotImplementedError("Renthop is not implemented")
