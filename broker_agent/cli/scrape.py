import asyncio
import logging
import random
import traceback
from collections.abc import Awaitable, Callable

import click
from playwright.async_api import Browser, Page, async_playwright

from broker_agent.common.enum import WebsiteType
from broker_agent.common.types import WebsiteScraper
from broker_agent.config.logging import configure_logging, get_logger
from broker_agent.config.settings import config
from broker_agent.pipeline.tasks import (
    scrape_streeteasy,
)

WEBSITE_SCRAPERS: dict[WebsiteType, WebsiteScraper] = {
    WebsiteType.STREETEASY: scrape_streeteasy,
    # TODO: Add back in when we have a working implementation for these websites
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

    async def _run_single_scraper(
        playwright,
        scraper: Callable[[Page], Awaitable[None]],
        website_name: str,
    ) -> None:
        """Helper to run an individual scraper inside its own headless browser."""
        browser: Browser = await playwright.chromium.launch(
            headless=config.browser.headless,
            args=config.browser.chrome_args,
            ignore_default_args=["--enable-automation"],
        )

        try:
            user_agent = random.choice(config.browser.user_agents)
            viewport = random.choice(config.browser.viewport_sizes)
            timezone_id = random.choice(config.browser.timezones)

            context = await browser.new_context(
                user_agent=user_agent,
                viewport=viewport,
                locale="en-US",
                timezone_id=timezone_id,
                device_scale_factor=random.choice([1, 2]),
                has_touch=random.choice([True, False]),
                permissions=["geolocation"],
                java_script_enabled=True,
                bypass_csp=True,
            )

            await context.route("**/*", lambda route: route.continue_())
            page = await context.new_page()
            logger.info(
                f"[{website_name}] Starting scraper in new browser instance with user agent: {user_agent}"
            )
            await scraper(page)

        except Exception as exc:
            logger.error(f"[{website_name}] Error occurred: {exc}")
            logger.debug(f"Call stack:\n{traceback.format_exc()}")
        finally:
            await browser.close()

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
                task = asyncio.create_task(
                    _run_single_scraper(
                        playwright, scraper_fn, f"{website_type.value} (instance {i+1})"
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


@click.command()
def run_scraper() -> None:
    asyncio.run(async_run_scraper())
