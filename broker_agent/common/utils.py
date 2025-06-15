import asyncio
import random
import re
import uuid
from datetime import datetime

from playwright.async_api import Locator, Page
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from broker_agent.config.logging import get_logger
from database.alembic.models.models import Apartment
from storage.minio_client import connector

logger = get_logger(__name__)


async def get_all_imgs_by_apt_id(
    apt_id: uuid.UUID, db_session: AsyncSession
) -> list[str]:
    """
    Get all images for an apartment.

    Args:
        apartment_id (uuid.UUID): The ID of the apartment.
        db_session (AsyncSession): Database session.

    Returns:
        list[str]: A list of image URLs.
    """
    query = select(Apartment).where(Apartment.apartment_id == apt_id)
    result = await db_session.execute(query)
    apartment = result.scalar_one_or_none()

    if not apartment:
        return []

    return apartment.image_urls


async def is_listing_duplicate(session: AsyncSession, listing_url: str) -> bool:
    """
    Checks if a listing with the given link already exists in the database.
    """
    result = await session.execute(
        select(Apartment).where(Apartment.link == listing_url)
    )
    exists = result.scalar_one_or_none() is not None
    return exists


def parse_availability_date(date_text: str) -> datetime:
    """
    Parses a date string from a listing into a datetime object.
    Handles various formats like "now", "MM/DD/YYYY", and "Mon DD".
    """
    if not date_text:
        return datetime.now()

    # Normalize whitespace and convert to lower case
    cleaned_text = re.sub(r"\s+", " ", date_text).strip().lower()

    if "now" in cleaned_text or not cleaned_text:
        return datetime.now()

    # Remove extra words that might interfere
    cleaned_text = cleaned_text.replace("availibility", "").strip()

    # Supported date formats, from most specific to least specific
    formats_to_try = [
        "%m/%d/%Y",  # "08/19/2024"
        "%b %d, %Y",  # "Aug 19, 2024"
        "%B %d, %Y",  # "August 19, 2024"
        "%b %d",  # "Aug 19"
        "%B %d",  # "August 19"
    ]

    now = datetime.now()

    for fmt in formats_to_try:
        try:
            parsed_date = datetime.strptime(cleaned_text, fmt)
            # If year is not parsed, it defaults to 1900. Fix it.
            if parsed_date.year == 1900:
                parsed_date = parsed_date.replace(year=now.year)
                # If the date is in the past for the current year, assume it's for the next year
                if parsed_date < now:
                    parsed_date = parsed_date.replace(year=now.year + 1)
            return parsed_date
        except ValueError:
            continue

    logger.warning(
        f"Could not parse availability date: '{date_text}', using current date."
    )
    return now


def parse_price_as_float(price_text: str) -> float:
    """
    Try to extract a float price from a messy price string.
    Looks for the first number (with optional decimal) in the string.
    """
    if not price_text:
        return 0.0
    cleaned = price_text.replace("$", "").replace(",", "")
    match = re.search(r"(\d+(?:\.\d+)?)", cleaned)
    if match:
        try:
            return float(match.group(1))
        except Exception as e:
            logger.warning(
                f"parse_price_as_float: Could not convert '{match.group(1)}' to float: {e}"
            )
            return 0.0
    logger.warning(
        f"parse_price_as_float: No number found in price text: '{price_text}'"
    )
    return 0.0


async def get_all_imgs_by_apt_id_as_base64(
    apt_id: uuid.UUID, db_session: AsyncSession
) -> list[dict]:
    """
    Get all images for an apartment as base64.

    Args:
        apt_id (uuid.UUID): The ID of the apartment.
        db_session (AsyncSession): Database session.

    Returns:
        list[dict]: A list of dicts, each containing:
            {
                "data": "<base64 data string>",
                "mime_type": "image/jpeg"  # or "image/png", etc.
            }
    """
    img_urls = await get_all_imgs_by_apt_id(apt_id, db_session)
    if not img_urls:
        return []

    results = []
    for url in img_urls:
        base64_data, mime_type = await connector.get_object_as_base64(url)
        results.append(
            {
                "data": base64_data,
                "mime_type": mime_type,
            }
        )
    return results


async def random_human_delay(min_ms=200, max_ms=900):
    await asyncio.sleep(random.uniform(min_ms, max_ms) / 1000.0)


async def get_text_content(locator: Locator, selector: str):
    try:
        return await locator.locator(selector).text_content(timeout=1000)
    except Exception:
        return None


async def random_extra_click(page: Page):
    # Randomly click somewhere on the page (e.g., header, footer, or a random button)
    # to simulate human behavior. This is a no-op if selector not found.
    selectors = [
        "header",
        "footer",
        "body",
        "nav",
        ".searchBar",
        ".site-logo",
        ".site-header",
    ]
    selector = random.choice(selectors)
    try:
        el = await page.query_selector(selector)
        if el:
            await el.click(timeout=500)
            await random_human_delay(100, 400)
    except Exception:
        pass  # Ignore if not clickable
