import asyncio
import random

from playwright.async_api import Page

from broker_agent.common.enum import ApartmentType
from broker_agent.common.utils import random_extra_click, random_human_delay
from broker_agent.config.settings import config


async def streeteasy_search(
    page: Page, min_price: int, max_price: int, apt_type: ApartmentType
):
    # Get elements using aria-labels and roles
    price_button = page.get_by_role("button", name="Price")
    bedrooms_select = page.get_by_label("Beds / Baths")
    no_fee_checkbox = page.get_by_label("No Fee Only")

    # Click the Price button to open price filter
    await price_button.click()
    await random_human_delay(300, 800)
    if random.random() < 0.5:
        await random_extra_click(page)

    # Click the no fee checkbox since its under the pricing menu
    no_fee_checkbox = page.get_by_label("No Fee Only")
    await no_fee_checkbox.click()
    await random_human_delay(200, 600)

    # Wait for and fill in min/max price fields
    await page.wait_for_selector("input[placeholder='No min']")
    min_price_input = page.get_by_placeholder("No min")
    await min_price_input.click()
    await random_human_delay(100, 400)
    await min_price_input.fill(str(min_price))
    await random_human_delay(200, 500)

    max_price_input = page.get_by_placeholder("Max")
    await max_price_input.click()
    await random_human_delay(100, 400)
    await max_price_input.fill(str(max_price))
    await random_human_delay(200, 500)

    # Press ESC to dismiss dropdown options that might be blocking the Done button
    await page.keyboard.press("Escape")
    await random_human_delay(100, 300)
    if random.random() < 0.3:
        await random_extra_click(page)

    # Select Studio from Bedrooms dropdown
    await bedrooms_select.click()
    await random_human_delay(200, 600)
    apt_type_option = page.get_by_test_id("desktop-filter").get_by_text(apt_type.value)
    await apt_type_option.click()
    await random_human_delay(200, 600)

    # Press ESC to dismiss dropdown options that might be blocking the Done button
    await page.keyboard.press("Escape")
    await random_human_delay(100, 300)
    if random.random() < 0.3:
        await random_extra_click(page)


async def _extract_listing_links_from_page(page: Page) -> set[str]:
    """Extracts all unique listing links from the current search results page."""
    links = set()

    # Extract from listing containers
    listing_containers = await page.query_selector_all(
        ".ListingCard-module__listingDetailsContainer"
    )
    for container in listing_containers:
        a_element = container.query_selector("a[href]")
        if a_element:
            href = await a_element.get_attribute("href")
            links.add(href)

    # Extract from anchor tags with address text action
    anchor_tags = await page.query_selector_all(
        "a.ListingDescription-module__addressTextAction___xAFZJ[href]"
    )
    for anchor in anchor_tags:
        href = await anchor.get_attribute("href")
        links.add(href)

    return links


async def _click_next_page_with_retries(
    page: Page,
    next_button,
    base_delay: float,
    max_delay: float,
    max_retries: int,
):
    """Attempts to click the 'Next Page' button with retries and human-like behavior."""
    retry_count = 0
    while retry_count < max_retries:
        try:
            if random.random() < 0.4:
                await random_extra_click(page)
            await random_human_delay(200, 800)
            await next_button.click()
            await page.wait_for_event("load", timeout=60000)
            break
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                raise e
            delay = min(base_delay * (2 ** (retry_count - 1)), max_delay)
            jitter = delay * 0.2 * (random.random() - 0.5)  # +/- 10% jitter
            actual_delay = delay + jitter
            await asyncio.sleep(actual_delay)


async def streeteasy_save_listings(
    page: Page,
    max_depth: int = config.streeteasy_max_depth,
    base_delay: float = config.streeteasy_base_delay,
    max_delay: float = config.streeteasy_max_delay,
    max_retries: int = config.streeteasy_max_retries,
) -> list[str]:
    """Scrape StreetEasy search result pages up to *max_depth* and collect listing URLs.

    Args:
        page (Page): The Playwright page instance pointing at the StreetEasy search results.
        max_depth (int, optional): Number of pagination pages to traverse. Defaults to the
            value configured in ``default.yaml`` via ``streeteasy_max_depth``.
        base_delay (float, optional): Starting delay in seconds. Defaults to the value
            configured in ``default.yaml`` via ``streeteasy_base_delay``.
        max_delay (float, optional): Maximum delay in seconds. Defaults to the value
            configured in ``default.yaml`` via ``streeteasy_max_delay``.
        max_retries (int, optional): Maximum number of retries. Defaults to the value
            configured in ``default.yaml`` via ``streeteasy_max_retries``.

    Returns:
        list[str]: A list of unique listing URLs discovered.
    """

    links: set[str] = set()
    i = 0

    while i < max_depth:
        # Extract links from the current page
        page_links = await _extract_listing_links_from_page(page)
        links.update(page_links)

        # Check for pagination region
        pagination = page.get_by_role("region", name="Pagination")
        if not pagination:
            break

        next_button = page.get_by_label("Next Page")

        # Try to click next page with retries and human-like behavior
        await _click_next_page_with_retries(
            page, next_button, base_delay, max_delay, max_retries
        )

        # Add a random delay and maybe a random click after each page
        await random_human_delay(400, 1200)
        if random.random() < 0.3:
            await random_extra_click(page)
        await asyncio.sleep(base_delay + (i * 1.5))
        i += 1

    return list(links)
