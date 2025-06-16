import asyncio

from playwright.async_api import Page

from broker_agent.common.utils import random_human_delay
from broker_agent.config.logging import get_logger

logger = get_logger(__name__)


async def advance_to_apartments_dot_com_start_page(
    page: Page,
    start_page: int,
    max_retries: int,
    base_delay: float,
    max_delay: float,
) -> int:
    """
    Helper to advance the Apartments.com search results to the desired start page.
    Returns the page number reached (should be start_page+1 if successful, or less if failed).
    """
    page_count = 1
    if start_page > 0:
        logger.info(f"Advancing to start page {start_page} (currently on page 1)...")
    while page_count < start_page + 1:
        next_button_selector = "#paging .next"
        next_button = page.locator(next_button_selector).first
        retry = 0
        while retry <= max_retries:
            if await next_button.is_visible():
                logger.info(f"Clicking next to reach start page: advancing from page {page_count} to {page_count+1}")
                try:
                    await next_button.click()
                    await random_human_delay(1500, 3500)
                    page_count += 1
                    break  # Success, break out of retry loop
                except Exception as e:
                    delay = min(base_delay * (2**retry), max_delay)
                    logger.warning(
                        f"Failed to navigate to next page (attempt {retry+1}/{max_retries}) while advancing to start page. "
                        f"Retrying after {delay:.1f}s. Error: {e}"
                    )
                    await asyncio.sleep(delay)
                    retry += 1
                    # Re-locate the next button in case DOM changed
                    next_button = page.locator(next_button_selector).first
            else:
                logger.info("No next page button found while advancing to start page. Stopping scrape.")
                return page_count
        else:
            logger.error(
                f"Exceeded max retries ({max_retries}) while advancing to start page. Stopping scrape."
            )
            return page_count
    return page_count
