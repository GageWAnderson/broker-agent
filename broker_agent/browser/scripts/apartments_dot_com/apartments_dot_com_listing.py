from datetime import datetime

from playwright._impl._errors import TargetClosedError
from playwright.async_api import Page, Playwright
from sqlalchemy.ext.asyncio import AsyncSession

from broker_agent.browser.scraping_browser import ScrapingBrowser
from broker_agent.common.exceptions import PageNavigationLimitReached
from broker_agent.common.utils import get_text_content
from broker_agent.config.logging import get_logger
from database.alembic.models.models import Apartment
from database.connection import async_db_session

logger = get_logger(__name__)

# NOTE: Apts dot com listings seem to be building-based
# Keep that in mind when scraping


async def process_apartments_dot_com_listings(
    playwright: Playwright,
    user_agent: str,
    listings: list[str],
) -> int:
    """
    Helper to process each listing URL in detail and save to DB.
    Returns the number of processed listings.
    """
    processed_count = 0
    try:
        async with async_db_session() as session:
            for i, listing_url in enumerate(listings):
                logger.info(f"Processing listing {i+1}/{len(listings)}: {listing_url}")
                try:
                    async with ScrapingBrowser(
                        playwright, user_agent, scrape_images=False
                    ) as listing_detail_page:
                        await _process_apartments_dot_com_listing(
                            listing_detail_page, listing_url, session
                        )
                        processed_count += 1
                except TargetClosedError as e:
                    logger.error(
                        f"Target closed while processing {listing_url}: {e}. "
                        f"Skipping this listing. {processed_count} listings processed so far."
                    )
                    continue
    except PageNavigationLimitReached:
        logger.warning(
            f"ScrapingBrowser encountered overall navigation limit. "
            f"Processed {processed_count} listings before stop."
        )
    return processed_count


async def _scrape_building_info(page: Page):
    name = await get_text_content(page, "h1.propertyName") or ""

    address_container = page.locator(".propertyAddressContainer")
    street_address = await get_text_content(address_container, ".delivery-address span")
    city = await get_text_content(page, 'a[data-type="city"]')
    state_zip_container = address_container.locator(".stateZipContainer")
    state = await get_text_content(state_zip_container, "span:first-child")
    zip_code = await get_text_content(state_zip_container, "span:last-child")
    full_address = f"{street_address}, {city}, {state} {zip_code}"
    neighborhood = await get_text_content(address_container, ".neighborhoodAddress")

    logger.info(f"Scraping apartment building: {name}")
    logger.info(f"Address: {full_address}")
    if neighborhood:
        logger.info(f"Neighborhood: {neighborhood}")

    return {
        "name": name,
        "full_address": full_address,
        "neighborhood": neighborhood,
        "address_container": address_container,
    }


async def _scrape_description(page: Page):
    description_locator = page.locator("#descriptionSection .descriptionText")
    description = ""
    if await description_locator.count() > 0:
        description_texts = await description_locator.all_text_contents()
        description = "\n".join(description_texts)
    return description


async def _scrape_image_urls(page: Page):
    image_urls = []
    gallery = page.locator("#media-gallery-container")
    if await gallery.is_visible():
        images = await gallery.locator("img").all()
        for img in images:
            src = await img.get_attribute("src")
            if src:
                image_urls.append(src)
    return image_urls


async def _scrape_unit_locators(page: Page):
    unit_locators = await page.locator(".pricingGridItem.mortar-wrapper").all()
    if not unit_locators:
        unit_locators = await page.locator("#availability-section .rentalGridRow").all()
    return unit_locators


async def _parse_unit(unit, name, description, listing_url, image_urls, neighborhood):
    price_text = await get_text_content(unit, ".rent")
    if not price_text:
        return None

    price = float(price_text.replace("$", "").replace(",", "").split(" - ")[0].strip())

    beds_text = await get_text_content(unit, ".beds .longText") or "0"
    try:
        num_beds = int(beds_text.split(" ")[0])
    except Exception:
        num_beds = 0

    baths_text = await get_text_content(unit, ".baths .longText") or "0"
    try:
        num_baths = float(baths_text.split(" ")[0])
    except Exception:
        num_baths = 0.0

    sqft_text = await get_text_content(unit, ".sqft .longText") or "0"
    try:
        sqft = int(sqft_text.replace(",", "").replace(" sq ft", "").strip())
    except Exception:
        sqft = 0

    available_date_text = await get_text_content(unit, ".available .date") or "now"
    available_date = datetime.now()
    if "now" not in available_date_text.lower():
        try:
            available_date = datetime.strptime(available_date_text, "%m/%d/%Y")
        except (ValueError, TypeError):
            logger.warning(
                f"Could not parse availability date: '{available_date_text}'"
            )

    unit_name_suffix = await get_text_content(unit, ".unit") or ""

    apartment = Apartment(
        name=f"{name} {unit_name_suffix}".strip(),
        price=price,
        description=description,
        available_date=available_date,
        days_on_market=0,  # Placeholder, hard to determine from page
        link=listing_url,
        image_urls=image_urls,
        sqft=sqft,
        num_beds=num_beds,
        num_baths=num_baths,
        neighborhood=neighborhood,
    )
    logger.info(f"Found unit: {apartment.name} - Price: {apartment.price}")
    return apartment


async def _process_apartments_dot_com_listing(
    page: Page, listing_url: str, session: AsyncSession
):
    """
    Scrapes an apartments.com listing page for apartment/building details.
    Given that apartments.com has listings for entire buildings, this function
    will attempt to find all individual units/floorplans and create a database
    entry for each.
    """
    await page.goto(listing_url, wait_until="domcontentloaded")

    try:
        await page.wait_for_selector("#propertyHeader", timeout=30000)
    except Exception:
        logger.error(
            "Could not find property header. It's possible the page didn't load correctly or is a different layout."
        )
        return

    building_info = await _scrape_building_info(page)
    name = building_info["name"]
    neighborhood = building_info["neighborhood"]

    description = await _scrape_description(page)
    image_urls = await _scrape_image_urls(page)
    unit_locators = await _scrape_unit_locators(page)

    if not unit_locators:
        logger.warning(
            f"No individual units found for {name}. The building may have no current availability or a different page layout."
        )
        return

    for unit in unit_locators:
        try:
            apartment = await _parse_unit(
                unit, name, description, listing_url, image_urls, neighborhood
            )
            if apartment:
                session.add(apartment)
        except Exception as e:
            logger.error(f"Failed to parse a unit for '{name}': {e}")

    await session.commit()
