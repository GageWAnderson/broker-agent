from playwright.async_api import Playwright

from broker_agent.browser.scraping_browser import ScrapingBrowser
from broker_agent.common.enum import WebsiteType
from broker_agent.common.exceptions import ScraperAccessDenied
from broker_agent.common.utils import random_human_delay
from broker_agent.config.logging import get_logger

logger = get_logger(__name__)

# TODO: Iterate page-by-page in a human-like way

async def get_apartments_dot_com_listings(
    playwright: Playwright, user_agent: str
) -> list[str]:
    try:
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
                raise ScraperAccessDenied(
                    "Access denied to Apartments.com for [Search]."
                )

            listings_selector = "article.placard"
            logger.info(
                f"Waiting for listings to appear with selector: '{listings_selector}'"
            )
            await page.wait_for_selector(listings_selector, timeout=30000)

            await random_human_delay()

            listing_elements = await page.query_selector_all(listings_selector)

            urls: list[str] = []
            for element in listing_elements:
                url = await element.get_attribute("data-url")
                if url:
                    urls.append(url)
                await random_human_delay(50, 250)

            logger.info(
                f"Found {len(urls)} listings on {WebsiteType.APARTMENTS_DOT_COM.value}"
            )
            return urls
    except Exception as e:
        logger.error(f"An error occurred while scraping apartments.com: {e}")
        return []
