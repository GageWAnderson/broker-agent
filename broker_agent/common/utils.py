import asyncio
import random
import uuid

from playwright.async_api import Page
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.alembic.models.models import Apartment
from storage.minio_client import connector


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
