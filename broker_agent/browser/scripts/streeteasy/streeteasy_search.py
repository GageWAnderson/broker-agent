import asyncio
import random

from playwright.async_api import Page

from broker_agent.common.enum import ApartmentType
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

    # Click the no fee checkbox since its under the pricing menu
    no_fee_checkbox = page.get_by_label("No Fee Only")
    await no_fee_checkbox.click()

    # Wait for and fill in min/max price fields
    await page.wait_for_selector("input[placeholder='No min']")
    min_price_input = page.get_by_placeholder("No min")
    await min_price_input.click()
    await min_price_input.fill(str(min_price))

    max_price_input = page.get_by_placeholder("Max")
    await max_price_input.click()
    await max_price_input.fill(str(max_price))

    # Press ESC to dismiss dropdown options that might be blocking the Done button
    await page.keyboard.press("Escape")

    # Select Studio from Bedrooms dropdown
    await bedrooms_select.click()
    apt_type_option = page.get_by_test_id("desktop-filter").get_by_text(apt_type.value)
    await apt_type_option.click()

    # Press ESC to dismiss dropdown options that might be blocking the Done button
    await page.keyboard.press("Escape")


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
        listing_containers = await page.query_selector_all(
            ".ListingCard-module__listingDetailsContainer"
        )

        for container in listing_containers:
            a_element = container.query_selector("a[href]")
            if a_element:
                href = await a_element.get_attribute("href")
                links.add(href)

        anchor_tags = await page.query_selector_all(
            "a.ListingDescription-module__addressTextAction___xAFZJ[href]"
        )
        for anchor in anchor_tags:
            href = await anchor.get_attribute("href")
            links.add(href)

        pagination = page.get_by_role("region", name="Pagination")

        if not pagination:
            break

        next_button = page.get_by_label("Next Page")

        retry_count = 0

        while retry_count < max_retries:
            try:
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

        await asyncio.sleep(base_delay + (i * 1.5))
        i += 1
    return list(links)
