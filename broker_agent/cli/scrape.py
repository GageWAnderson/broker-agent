import asyncio
import traceback

import click
from playwright.async_api import async_playwright

from broker_agent.common.enum import WebsiteType
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

configure_logging(log_level=config.log_level)

logger = get_logger(__name__)

async def async_run_scraper() -> None:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)

        for website in config.websites:
            website_type = None

            # Check if the website is in our enum
            try:
                website_type = WebsiteType(website)
            except ValueError:
                logger.error(f"Website {website} not supported")
                continue

            if website_type not in WEBSITE_SCRAPERS:
                logger.error(f"Website {website_type} has no scraper implementation")
                continue

            try:
                logger.info(f"Navigating to {website}")
                page = await browser.new_page()
                await WEBSITE_SCRAPERS[website_type](page)
            except Exception as e:
                logger.error(f"Error processing {website}: {e}")
                logger.error(f"Call stack:\n{traceback.format_exc()}")
                await page.close()
            break

        await browser.close()


@click.command()
def run_scraper() -> None:
    asyncio.run(async_run_scraper())
