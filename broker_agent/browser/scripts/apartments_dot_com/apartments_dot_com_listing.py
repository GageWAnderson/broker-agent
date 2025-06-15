from playwright.async_api import Page
from sqlalchemy.ext.asyncio import AsyncSession


async def process_apartments_dot_com_listings(
    page: Page, listing_url: str, session: AsyncSession
):
    pass
