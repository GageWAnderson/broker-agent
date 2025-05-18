import asyncio
import logging
import traceback
from collections.abc import Awaitable, Callable

import click
from playwright.async_api import Page, Playwright, async_playwright

from broker_agent.browser.scraping_browser import ScrapingBrowser
from broker_agent.browser.user_agent_rotator import UserAgentRotator
from broker_agent.common.enum import WebsiteType
from broker_agent.common.types import WebsiteScraper
from broker_agent.config.logging import configure_logging, get_logger
from broker_agent.config.settings import config
from broker_agent.pipeline.tasks import (
    scrape_streeteasy,
)

WEBSITE_SCRAPERS: dict[WebsiteType, WebsiteScraper] = {
    WebsiteType.STREETEASY: scrape_streeteasy,
    # WebsiteType.APARTMENTS_DOT_COM: scrape_apartments_dot_com,
    # WebsiteType.RENTHOP: scrape_renthop,
}

configure_logging(log_level=config.log_level)

logger = get_logger(__name__)

logging.getLogger("httpx").setLevel(logging.WARNING)


async def async_run_scraper() -> None:
    """Launch multiple headless browsers concurrently and run website scrapers.

    The number of parallel browsers per website is defined by ``config.parallel_browsers``
    if present (defaulting to 3). All websites are scraped concurrently, with each website
    having multiple browser instances working on it simultaneously.
    """

    if not config.browser_settings.user_agents:
        logger.error("User agent list is empty. Cannot proceed with rotation.")
        return

    user_agent_rotator = UserAgentRotator(config.browser_settings.user_agents)

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
                        user_agent_rotator,
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
    scraper: Callable[[Page], Awaitable[None]],
    website_name: str,
    ua_rotator: UserAgentRotator,
) -> None:
    """Helper to run an individual scraper inside its own headless browser."""
    try:
        async with ScrapingBrowser(playwright, ua_rotator, website_name) as page:
            await scraper(page)
    except Exception as exc:
        logger.error(f"[{website_name}] Error occurred: {exc}")
        logger.debug(f"Call stack:\n{traceback.format_exc()}")


@click.command()
def run_scraper() -> None:
    asyncio.run(async_run_scraper())
