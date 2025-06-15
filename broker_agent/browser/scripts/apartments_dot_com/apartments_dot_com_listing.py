from playwright._impl._errors import TargetClosedError
from playwright.async_api import Page, Playwright
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from broker_agent.browser.scraping_browser import ScrapingBrowser
from broker_agent.common.exceptions import PageNavigationLimitReached
from broker_agent.common.utils import (
    get_text_content,
    is_listing_duplicate,
    parse_availability_date,
    parse_price_as_float,
)
from broker_agent.config.logging import get_logger
from database.alembic.models.models import Apartment
from database.connection import async_db_session

logger = get_logger(__name__)

# TODO: Handle listings for individual units


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
                # Check for duplicate before scraping
                if await is_listing_duplicate(session, listing_url):
                    logger.warning(
                        f"Duplicate listing found for link '{listing_url}'. Skipping insertion."
                    )
                    continue
                try:
                    async with ScrapingBrowser(
                        playwright, user_agent, scrape_images=False
                    ) as listing_detail_page:
                        try:
                            await _process_apartments_dot_com_listing(
                                listing_detail_page, listing_url, session
                            )
                            processed_count += 1
                        except IntegrityError as e:
                            # Handle unique constraint violation gracefully
                            if "apartments_link_key" in str(e.orig):
                                logger.warning(
                                    f"Duplicate listing found for link '{listing_url}'. Skipping insertion."
                                )
                                await session.rollback()
                            else:
                                logger.error(
                                    f"IntegrityError while processing {listing_url}: {e}"
                                )
                                await session.rollback()
                        except Exception as e:
                            logger.error(
                                f"Unexpected error while processing {listing_url}: {e}"
                            )
                            await session.rollback()
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

    # Log what was scraped if it exists
    if name:
        logger.debug(f"Scraped building name: {name}")
    if street_address or city or state or zip_code:
        logger.debug(
            f"Scraped address parts: street='{street_address}', city='{city}', state='{state}', zip='{zip_code}'"
        )
    if full_address:
        logger.debug(f"Scraped full address: {full_address}")
    if neighborhood:
        logger.debug(f"Scraped neighborhood: {neighborhood}")

    return {
        "name": name,
        "full_address": full_address,
        "neighborhood": neighborhood,
        "address_container": address_container,
    }


async def _scrape_description(page: Page):
    description_parts = []

    # Scrape about snippet
    about_snippet_locator = page.locator("#aboutSectionSnippet .aboutSnippet")
    if await about_snippet_locator.count() > 0:
        about_texts = await about_snippet_locator.all_text_contents()
        description_parts.extend(about_texts)
        if about_texts:
            logger.debug(f"Scraped about snippet: {about_texts}")

    # Scrape original description section
    description_locator = page.locator("#descriptionSection .descriptionText")
    if await description_locator.count() > 0:
        description_texts = await description_locator.all_text_contents()
        description_parts.extend(description_texts)
        if description_texts:
            logger.debug(f"Scraped description section: {description_texts}")

    description = "\n".join(part.strip() for part in description_parts if part.strip())
    if description:
        logger.info(
            f"Scraped description: {description[:200]}{'...' if len(description) > 200 else ''}"
        )
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
    if image_urls:
        logger.info(f"Scraped {len(image_urls)} image URLs.")
        logger.debug(f"Image URLs: {image_urls}")
    else:
        logger.info("No image URLs scraped.")
    return image_urls


async def _scrape_floor_plan_locators(page: Page):
    unit_locators = await page.locator(
        ".pricingGridItem.mortar-wrapper, .pricingGridItem.hasUnitGrid"
    ).all()
    if not unit_locators:
        unit_locators = await page.locator("#availability-section .rentalGridRow").all()
    if unit_locators:
        logger.info(f"Scraped {len(unit_locators)} floor plan locators.")
    else:
        logger.info("No floor plan locators scraped.")
    return unit_locators


async def _parse_unit_row(
    unit_row,
    model_name,
    name,
    description,
    listing_url,
    image_urls,
    num_beds,
    num_baths,
    neighborhood,
    full_address,
):
    try:
        logger.debug(f"Parsing unit row for model '{model_name}'")
        unit_name_suffix = await get_text_content(unit_row, ".unitColumn") or ""
        logger.debug(f"Unit name suffix: '{unit_name_suffix}'")
        price_text = await get_text_content(unit_row, ".pricingColumn") or "0"
        logger.debug(f"Price text: '{price_text}'")
        sqft_text = await get_text_content(unit_row, ".sqftColumn") or "0"
        logger.debug(f"Sqft text: '{sqft_text}'")
        available_date_text = (
            await get_text_content(unit_row, ".availableColumn") or "now"
        )
        logger.debug(f"Available date text: '{available_date_text}'")

        price = parse_price_as_float(price_text)
        logger.debug(f"Parsed price: {price}")
        sqft = (
            int(sqft_text.replace(",", "").strip())
            if sqft_text and sqft_text.replace(",", "").strip().isdigit()
            else 0
        )
        logger.debug(f"Parsed sqft: {sqft}")

        available_date = parse_availability_date(available_date_text)
        logger.debug(f"Parsed available date: {available_date}")

        apartment = Apartment(
            name=f"{name} {model_name} {unit_name_suffix}".strip(),
            price=price,
            description=description,
            available_date=available_date,
            days_on_market=0,
            link=listing_url,
            image_urls=image_urls,
            sqft=sqft,
            num_beds=num_beds,
            num_baths=num_baths,
            neighborhood=neighborhood,
        )
        logger.info(
            f"Parsed unit: {apartment.name} - Price: {apartment.price}, SqFt: {apartment.sqft}"
        )
        return apartment
    except Exception as e:
        logger.error(f"Failed to parse a unit row for floor plan '{model_name}': {e}")
        return None


async def _parse_floor_plan_and_units(
    floor_plan_locator,
    name,
    description,
    listing_url,
    image_urls,
    neighborhood,
    full_address,
):
    """
    Parse a floor plan and its units. Look for individual units within the floor plan.
    """
    apartments = []
    logger.debug("Parsing floor plan and units for building: '%s'", name)
    model_name = await get_text_content(floor_plan_locator, ".modelName")
    logger.debug(f"Model name scraped: '{model_name}'")
    details_text_wrapper = floor_plan_locator.locator(".detailsTextWrapper")
    details_spans = await details_text_wrapper.locator("span").all()
    logger.debug(f"Details spans found: {len(details_spans)}")

    beds_text, baths_text = "0", "0"
    if details_spans:
        beds_text = await details_spans[0].text_content() or "0"
        logger.debug(f"Beds text scraped: '{beds_text}'")
        if len(details_spans) > 1:
            baths_text = await details_spans[1].text_content() or "0"
            logger.debug(f"Baths text scraped: '{baths_text}'")

    num_beds = 0
    if "studio" in beds_text.lower():
        num_beds = 0
        logger.debug("Detected studio unit, setting num_beds to 0")
    else:
        try:
            num_beds = int(beds_text.split(" ")[0])
            logger.debug(f"Parsed num_beds: {num_beds}")
        except (ValueError, IndexError):
            logger.warning(f"Could not parse number of beds from text: '{beds_text}'")
            num_beds = 0

    try:
        num_baths = float(baths_text.split(" ")[0])
        logger.debug(f"Parsed num_baths: {num_baths}")
    except (ValueError, IndexError):
        logger.warning(f"Could not parse number of baths from text: '{baths_text}'")
        num_baths = 0.0

    unit_rows = await floor_plan_locator.locator(".unitContainer").all()
    logger.debug(f"Unit rows found: {len(unit_rows)}")

    if unit_rows:
        logger.info(
            f"Found {len(unit_rows)} individual units for floor plan '{model_name}'."
        )
        apartments = [
            apartment
            for idx, unit_row in enumerate(unit_rows)
            if (
                apartment := await _parse_unit_row(
                    unit_row,
                    model_name,
                    name,
                    description,
                    listing_url,
                    image_urls,
                    num_beds,
                    num_baths,
                    neighborhood,
                    full_address,
                )
            )
        ]
    else:
        logger.debug(f"No unit rows found for floor plan '{model_name}'.")

    logger.info(
        f"Total apartments parsed for floor plan '{model_name}': {len(apartments)}"
    )
    return apartments


async def _handle_single_unit_listing(
    page: Page,
    name: str,
    description: str,
    listing_url: str,
    image_urls: list[str],
    neighborhood: str,
    full_address: str,
    session: AsyncSession,
) -> bool:
    """
    Handles scraping for listings that don't have floor plans but have a single price info section.
    Returns True if a single unit was found and processed, False otherwise.
    """
    price_info_wrapper = page.locator("#priceBedBathAreaInfoWrapper")
    if await price_info_wrapper.count() == 0:
        return False

    logger.info(
        "No floor plans found, but price/bed/bath info is available. Scraping as single unit."
    )
    rent_info_items = await price_info_wrapper.locator(
        ".priceBedRangeInfo li.column"
    ).all()

    price_text, beds_text, baths_text, sqft_text = "", "", "", ""

    for item in rent_info_items:
        label_el = item.locator(".rentInfoLabel")
        detail_el = item.locator(".rentInfoDetail")
        if await label_el.count() > 0 and await detail_el.count() > 0:
            label = (await label_el.text_content() or "").lower()
            detail_text = (await detail_el.text_content() or "").strip()
            if "monthly rent" in label:
                price_text = detail_text
            elif "bedrooms" in label:
                beds_text = detail_text
            elif "bathrooms" in label:
                baths_text = detail_text
            elif "square feet" in label:
                sqft_text = detail_text

    price = parse_price_as_float(price_text)
    num_beds = (
        0
        if "studio" in beds_text.lower()
        else (
            int(beds_text.split(" ")[0])
            if beds_text and beds_text.split(" ")[0].isdigit()
            else 0
        )
    )
    num_baths = (
        float(baths_text.split(" ")[0])
        if baths_text and baths_text.split(" ")[0].replace(".", "", 1).isdigit()
        else 0.0
    )
    sqft = (
        int(sqft_text.replace(",", "").strip())
        if sqft_text and sqft_text.replace(",", "").replace("--", "").strip().isdigit()
        else 0
    )

    available_date_text = "now"
    avail_loc = page.locator(".availabilityInfo, .availableText, .unitAvailDate").first
    if await avail_loc.count() > 0:
        available_date_text = await avail_loc.text_content() or "now"
    available_date = parse_availability_date(available_date_text)

    apartment = Apartment(
        name=name,
        price=price,
        description=description,
        available_date=available_date,
        days_on_market=0,
        link=listing_url,
        image_urls=image_urls,
        sqft=sqft,
        num_beds=num_beds,
        num_baths=num_baths,
        neighborhood=neighborhood,
    )

    session.add(apartment)
    try:
        await session.commit()
        logger.info(
            f"Added single unit apartment to DB for {name} from price info section."
        )
    except IntegrityError:
        await session.rollback()
        logger.warning(
            f"Duplicate single unit apartment found for link '{listing_url}'. Skipping."
        )
    return True


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

    # Step 1: Wait for property header
    if not await _wait_for_property_header(page):
        logger.error(
            "Could not find property header. It's possible the page didn't load correctly or is a different layout."
        )
        return

    # Step 2: Scrape building info, description, images, and floor plans
    building_info = await _scrape_building_info(page)
    name = building_info["name"]
    neighborhood = building_info["neighborhood"]
    full_address = building_info["full_address"]

    description = await _scrape_description(page)
    image_urls = await _scrape_image_urls(page)
    floor_plan_locators = await _scrape_floor_plan_locators(page)

    _log_scraped_sections(
        name, neighborhood, description, image_urls, floor_plan_locators
    )

    # Step 3: Handle no floor plans (single unit or warning)
    if not floor_plan_locators:
        processed_as_single_unit = await _handle_single_unit_listing(
            page,
            name,
            description,
            listing_url,
            image_urls,
            neighborhood,
            full_address,
            session,
        )
        if processed_as_single_unit:
            return

        logger.warning(
            f"No individual units found for {name}. The building may have no current availability or a different page layout."
        )
        return

    # Step 4: Parse and add apartments to DB
    await _add_apartments_from_floor_plans(
        floor_plan_locators,
        name,
        description,
        listing_url,
        image_urls,
        neighborhood,
        full_address,
        session,
    )


async def _wait_for_property_header(page: Page) -> bool:
    try:
        await page.wait_for_selector("#propertyHeader", timeout=30000)
        return True
    except Exception:
        return False


def _log_scraped_sections(
    name, neighborhood, description, image_urls, floor_plan_locators
):
    if name:
        logger.info(f"Building name scraped: {name}")
    if neighborhood:
        logger.info(f"Neighborhood scraped: {neighborhood}")
    if description:
        logger.info(
            f"Description scraped: {description[:200]}{'...' if len(description) > 200 else ''}"
        )
    if image_urls:
        logger.info(f"Image URLs scraped: {len(image_urls)} images")
    if floor_plan_locators:
        logger.info(
            f"Floor plan locators scraped: {len(floor_plan_locators)} floor plans"
        )


async def _add_apartments_from_floor_plans(
    floor_plan_locators,
    name,
    description,
    listing_url,
    image_urls,
    neighborhood,
    full_address,
    session,
):
    apartments_to_add = []
    for floor_plan_locator in floor_plan_locators:
        apartments = await _parse_floor_plan_and_units(
            floor_plan_locator,
            name,
            description,
            listing_url,
            image_urls,
            neighborhood,
            full_address,
        )
        for apartment in apartments:
            if apartment:
                apartments_to_add.append(apartment)

    for apartment in apartments_to_add:
        session.add(apartment)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        logger.warning(
            f"Duplicate listing found for link '{apartment.link}'. Skipping insertion."
        )

    logger.info(f"Added {len(apartments_to_add)} apartments to DB.")
