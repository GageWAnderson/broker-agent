import asyncio
import re
from datetime import datetime

from playwright.async_api import Page
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from broker_agent.browser.utils import get_text_content_with_timeout
from broker_agent.config.logging import get_logger
from database.alembic.models.models import Apartment, PriceHistory
from storage.minio_client import connector as minio_connector

logger = get_logger(__name__)


async def scrape_listing_details(page: Page) -> dict[str, any]:
    selectors = {
        "name": '[data-testid="homeAddress"]',
        "price": '[data-testid="priceInfo"]',
        "description": '[data-testid="about-section"]',
        "available_date": '[data-testid="rentalListingSpec-available"]',
        "days_on_market": '[data-testid="rentalListingSpec-daysOnMarket"]',
        "policies": '[data-testid="home-features-section"]',
        "home_features": '[data-testid="home-features-section"]',
        "ammenities": '[data-testid="building-amenities-section"]',
    }
    apartment_data = {key: None for key in selectors.keys()}
    tasks = {
        field: get_text_content_with_timeout(page, selector)
        for field, selector in selectors.items()
    }
    results = await asyncio.gather(*tasks.values())

    for field, result in zip(tasks.keys(), results, strict=False):
        apartment_data[field] = result

    image_urls = await get_image_urls(page)
    apartment_data["image_urls"] = image_urls

    price_history = await get_price_history(page)
    apartment_data["price_history"] = price_history

    similar_listings = await get_similar_listings(page)
    apartment_data["similar_listings"] = similar_listings

    return apartment_data


async def get_price_history(page: Page) -> list[dict[str, datetime | float]]:
    price_history = []
    try:
        # Find all table rows in the price history table
        rows = await page.query_selector_all("table.styled__Table-sc-z1hsf2-1 tbody tr")

        for row in rows:
            date_element = await row.query_selector("td:first-child p")
            price_element = await row.query_selector("td:nth-child(2) p:first-child b")

            if date_element and price_element:
                date_text_content = await date_element.text_content()
                price_text_content = await price_element.text_content()

                parsed_date: datetime | None = None
                if date_text_content:
                    try:
                        # Strip the word 'Available' from the date string if present
                        cleaned_date_text = date_text_content.replace(
                            "Available", ""
                        ).strip()
                        # Parse date string e.g., "4/30/2025"
                        parsed_date = datetime.strptime(cleaned_date_text, "%m/%d/%Y")
                    except ValueError:
                        logger.warning(
                            f"Failed to parse date string: {date_text_content}"
                        )

                parsed_price: float | None = None
                if price_text_content:
                    # Extract the numeric value from the price text (e.g., "$7,600" -> 7600)
                    price_match = re.search(r"\$([0-9,]+)", price_text_content)
                    if price_match:
                        price_str = price_match.group(1).replace(",", "")
                        try:
                            parsed_price = float(price_str)
                        except ValueError:
                            logger.warning(
                                f"Failed to convert price string to float: {price_str}"
                            )

                if parsed_date and parsed_price is not None:
                    price_history.append({"date": parsed_date, "price": parsed_price})

    except Exception as e:
        logger.error(f"Error extracting price history: {e}")

    return price_history


async def get_similar_listings(page: Page) -> list[str]:
    similar_listings = []
    try:
        listing_cards = await page.query_selector_all(
            "div.ListingCard-module__cardContainer___0d8UM"
        )

        logger.info(f"Found {len(listing_cards)} similar listing cards")

        async def extract_link(card):
            link_element = await card.query_selector(
                "a.text-action_baseTextAction_QUkYk"
            )
            if link_element:
                href = await link_element.get_attribute("href")
                if href:
                    if href.startswith("/"):
                        href = f"https://streeteasy.com{href}"
                    logger.debug(f"Found similar listing: {href}")
                    return href
            return None

        tasks = [extract_link(card) for card in listing_cards]
        results = await asyncio.gather(*tasks)

        similar_listings = [link for link in results if link]

        logger.debug(f"Extracted {len(similar_listings)} similar listing links")
    except Exception as e:
        logger.error(f"Error extracting similar listings: {e}")

    return similar_listings


async def get_image_urls(page: Page) -> list[str]:
    image_urls = set()
    current_photo_num = 1
    seen_alt_texts = set()

    while True:
        try:
            # Look for images with alt text pattern "photo n"
            selector = (
                f"img[alt='photo {current_photo_num}'][class*='MediaCarousel_contain']"
            )
            image_element = await page.query_selector(selector)

            if not image_element:
                break

            image_url = await image_element.get_attribute("src")
            alt_text = await image_element.get_attribute("alt")

            if not image_url or alt_text in seen_alt_texts:
                logger.warning(f"Duplicate or missing image found: {alt_text}")
                break

            seen_alt_texts.add(alt_text)
            image_urls.add(image_url)

            # Move to next photo number
            current_photo_num += 1

            # Click next button to ensure all images are loaded in the DOM
            # Use first() to select the first element when multiple elements match
            next_button = page.get_by_test_id("next-image-button").first
            await next_button.click(timeout=2000)
            await page.wait_for_timeout(500)  # Small delay for image to load

        except Exception as e:
            logger.error(f"Error getting image URL for photo {current_photo_num}: {e}")
            break

    logger.info(f"Found {len(image_urls)} unique images")
    return list(image_urls)


async def save_listings_to_db(listings: list[dict[str, any]], session: AsyncSession):
    """
    Save apartment listings to the database.

    Args:
        listings: List of listing details to save
        Session: SQLAlchemy sessionmaker
    """
    # Use a with block to manage the session lifecycle
    for listing in listings:
        try:
            # Check if the apartment already exists
            if not await _apartment_exists(session, listing):
                # Process and add the apartment
                await _process_and_add_apartment(session, listing)
        except IntegrityError as conflict_error:
            await session.rollback()
            logger.warning(
                f"Conflict or unique violation for listing {listing.get('link', 'unknown')}: {conflict_error}"
            )
            continue  # Continue with the next listing
        except Exception as e:
            await session.rollback()
            logger.error(
                f"Error processing listing {listing.get('link', 'unknown')}: {e}"
            )
            continue  # Continue with the next listing

    # Commit the session at the end
    try:
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error(f"Error committing to database: {e}")


async def _apartment_exists(db_session: AsyncSession, listing: dict[str, any]) -> bool:
    """
    Check if an apartment with the given link already exists in the database asynchronously.

    Args:
        db_session: SQLAlchemy AsyncSession
        listing: Apartment listing data

    Returns:
        True if apartment exists, False otherwise
    """
    stmt = select(Apartment).where(Apartment.link == listing["link"])
    result = await db_session.execute(stmt)
    existing_apartment = result.scalars().first()
    return existing_apartment is not None


async def _process_and_add_apartment(
    db_session: AsyncSession, listing: dict[str, any]
) -> None:
    """
    Process listing data, upload images to Minio, and add a new apartment to the database.

    Args:
        db_session: SQLAlchemy AsyncSession
        listing: Apartment listing data
    """
    days_on_market = _extract_days_on_market(listing)
    available_date = _parse_available_date(listing)
    price = _parse_price(listing)

    # Download images and upload to Minio concurrently
    image_tasks = [
        minio_connector.download_image(url) for url in listing.get("image_urls", [])
    ]
    minio_results = await asyncio.gather(*image_tasks)
    minio_image_urls = [url for url in minio_results if url is not None]

    new_apartment = Apartment(
        name=listing["name"],
        price=price,
        description=listing["description"],
        available_date=available_date,
        days_on_market=days_on_market,
        link=listing["link"],
        image_urls=minio_image_urls,
        similar_listings=listing["similar_listings"],
    )
    db_session.add(new_apartment)
    await db_session.flush()

    # Process price history if available
    if "price_history" in listing and listing["price_history"]:
        for price_point in listing["price_history"]:
            price_history_entry = PriceHistory(
                apartment_id=new_apartment.apartment_id,
                price=price_point["price"],
                date=price_point["date"],
            )
            db_session.add(price_history_entry)
        await db_session.flush()


def _extract_days_on_market(listing: dict[str, any]) -> int:
    """
    Extract days on market from listing data.

    Args:
        listing: Apartment listing data

    Returns:
        Number of days on market as integer
    """
    days_on_market = 0
    try:
        if isinstance(listing["days_on_market"], str):
            # Extract numeric value from string like "Days on market50 days"
            days_match = re.search(r"(\d+)", listing["days_on_market"])
            if days_match:
                days_on_market = int(days_match.group(1))
    except Exception as e:
        print(
            f"Warning: Could not parse days_on_market from {listing['days_on_market']}: {e}"
        )
    return days_on_market


def _parse_available_date(listing: dict[str, any]) -> datetime:
    """
    Parse available date from listing data.

    Args:
        listing: Apartment listing data

    Returns:
        Available date as datetime object
    """
    available_date = datetime.now()
    try:
        if isinstance(listing["available_date"], str):
            if "Available now" in listing["available_date"]:
                available_date = datetime.now()
            else:
                # Try to extract date if in standard format
                available_date = datetime.strptime(
                    listing["available_date"], "%Y-%m-%d"
                )
    except Exception as e:
        print(
            f"Warning: Could not parse available_date from {listing['available_date']}: {e}"
        )
    return available_date


def _parse_price(listing: dict[str, any]) -> float:
    """
    Parse price from listing data.

    Args:
        listing: Apartment listing data

    Returns:
        Price as float
    """
    price = 0
    try:
        if isinstance(listing["price"], str):
            # Extract the first price value (e.g., $3,146)
            price_match = re.search(r"\$([0-9,]+)", listing["price"])
            if price_match:
                # Remove commas and convert to float
                price = float(price_match.group(1).replace(",", ""))
        elif isinstance(listing["price"], int | float):
            price = float(listing["price"])
    except Exception as e:
        print(f"Warning: Could not parse price from {listing['price']}: {e}")
    return price
