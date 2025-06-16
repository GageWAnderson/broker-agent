import asyncio
import logging
import traceback

import click
from playwright.async_api import Playwright, async_playwright

from broker_agent.browser.utils import generate_random_user_agent
from broker_agent.common.enum import WebsiteType
from broker_agent.common.exceptions import ScraperAccessDenied
from broker_agent.common.types import WebsiteScraper
from broker_agent.config.logging import configure_logging, get_logger
from broker_agent.config.settings import config
from broker_agent.pipeline.tasks import (
    scrape_apartments_dot_com,
    scrape_renthop,
    scrape_streeteasy,
)

WEBSITE_SCRAPERS: dict[WebsiteType, WebsiteScraper] = {
    WebsiteType.STREETEASY: scrape_streeteasy,
    WebsiteType.APARTMENTS_DOT_COM: scrape_apartments_dot_com,
    WebsiteType.RENTHOP: scrape_renthop,
}

configure_logging(log_level=config.LOGGING_LEVEL)

logger = get_logger(__name__)

logging.getLogger("httpx").setLevel(logging.WARNING)


async def async_run_scraper() -> None:
    """Launch multiple headless browsers concurrently and run website scrapers.

    The number of parallel browsers per website is defined by ``config.parallel_browsers``
    if present (defaulting to 3). All websites are scraped concurrently, with each website
    having multiple browser instances working on it simultaneously.
    """

    async with async_playwright() as playwright:
        all_tasks: list[asyncio.Task[None]] = []
        for website in config.websites:
            try:
                website_type = WebsiteType(website)
            except ValueError:
                logger.error(f"Website {website} not supported")
                continue

            scraper_fn = WEBSITE_SCRAPERS.get(website_type)
            if scraper_fn is None:
                logger.error(
                    f"Website {website_type} has no scraper implementation configured"
                )
                continue

            website_tasks = []
            for i in range(config.parallel_browsers):
                instance_name = f"{website_type.value} (instance {i+1})"
                task = asyncio.create_task(
                    _run_single_scraper(
                        playwright,
                        scraper_fn,
                        instance_name,
                    )
                )
                website_tasks.append(task)
                all_tasks.append(task)

            logger.info(
                f"Scheduled {len(website_tasks)} parallel scrapers for {website_type.value}"
            )

        if all_tasks:
            await asyncio.gather(*all_tasks)
        else:
            logger.warning("No valid scraper tasks were scheduled, exiting.")


async def _run_single_scraper(
    playwright: Playwright,
    scraper_fn: WebsiteScraper,
    website_name: str,
) -> None:
    """Helper to run an individual scraper inside its own headless browser with retry logic."""
    max_retries = config.browser_settings.max_retries

    for attempt in range(max_retries):
        user_agent = generate_random_user_agent()
        try:
            logger.debug(
                f"[{website_name}] Attempt {attempt + 1}/{max_retries} to scrape with user agent: {user_agent[:30]}..."
            )
            await scraper_fn(playwright, user_agent)
            logger.info(
                f"[{website_name}] Successfully completed scraping attempt {attempt + 1}."
            )
            break
        except ScraperAccessDenied as e:
            logger.warning(
                f"[{website_name}] Access denied on attempt {attempt + 1}/{max_retries}: {e}"
            )
            if attempt + 1 == max_retries:
                logger.error(
                    f"[{website_name}] Failed to scrape after {max_retries} attempts due to access denial."
                )
            else:
                logger.info(f"[{website_name}] Retrying with a new user agent...")
        except Exception as e:
            logger.error(
                f"[{website_name}] An unexpected error occurred on attempt {attempt + 1}/{max_retries}: {e}"
            )
            logger.error(traceback.format_exc())
            if attempt + 1 == max_retries:
                logger.error(
                    f"[{website_name}] Failed to scrape after {max_retries} attempts due to unexpected errors."
                )
            else:
                logger.info(
                    f"[{website_name}] Retrying with a new user agent due to unexpected error..."
                )


@click.command()
def run_scraper() -> None:
    asyncio.run(async_run_scraper())
