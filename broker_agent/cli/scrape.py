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

# List of common user agents to rotate through
COMMON_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
]

# List of common viewport sizes
VIEWPORT_SIZES = [
    {"width": 1366, "height": 768},
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
    {"width": 1536, "height": 864},
]

# List of timezones for randomization
TIMEZONES = [
    "America/New_York",
    "America/Chicago",
    "America/Los_Angeles",
    "America/Denver",
]


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
        # Launch browser with anti-detection features
        browser: Browser = await playwright.chromium.launch(
            headless=False,  # Non-headless mode is less detectable
            args=[
                "--disable-blink-features=AutomationControlled",  # Hide automation flag
                "--disable-features=IsolateOrigins,site-per-process",  # Disable site isolation
                "--enable-webgl",  # Enable WebGL
                "--use-gl=swiftshader",  # Use software rendering
                "--enable-accelerated-2d-canvas",  # Enable hardware acceleration
                "--no-sandbox",  # Less secure but more stable
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",  # Overcome limited resource problems
                "--disable-accelerated-2d-canvas",
                "--disable-gpu",  # Software rendering is more consistent
                "--window-size=1920,1080",  # Standard window size
            ],
            ignore_default_args=["--enable-automation"],  # Remove automation flag
        )

        try:
            # Get random properties for this browser instance to appear unique
            user_agent = random.choice(COMMON_USER_AGENTS)
            viewport = random.choice(VIEWPORT_SIZES)
            timezone_id = random.choice(TIMEZONES)

            # Create a context with anti-fingerprinting settings
            context = await browser.new_context(
                user_agent=user_agent,
                viewport=viewport,
                locale="en-US",
                timezone_id=timezone_id,
                device_scale_factor=random.choice([1, 2]),  # Vary between standard and retina
                has_touch=random.choice([True, False]),  # Randomize touch capability
                permissions=["geolocation"],  # Grant common permissions
                java_script_enabled=True,
                bypass_csp=True,  # Bypass Content Security Policy
            )

            # Enable caching for more human-like behavior
            await context.route("**/*", lambda route: route.continue_())

            # Add a small delay to simulate page load like a human
            page = await context.new_page()
            logger.info(f"[{website_name}] Starting scraper in new browser instance with user agent: {user_agent}")

            # Run the scraper with the configured page
            await scraper(page)

        except Exception as exc:
            logger.error(f"[{website_name}] Error occurred: {exc}")
            logger.debug(f"Call stack:\n{traceback.format_exc()}")
        finally:
            await browser.close()

    async with async_playwright() as playwright:
        all_tasks: list[asyncio.Task[None]] = []

        # Process all websites concurrently
        for website in config.websites:
            # Validate website type
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

            # Create multiple browser instances for each website
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
