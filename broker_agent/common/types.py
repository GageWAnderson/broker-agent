from typing import Protocol

from playwright.async_api import Page


class WebsiteScraper(Protocol):
    async def __call__(
        self, page: Page, error_message: str | None = None
    ) -> None: ...
