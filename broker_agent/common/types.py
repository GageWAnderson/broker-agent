from collections.abc import Awaitable, Callable

from playwright.async_api import Playwright

WebsiteScraper = Callable[[Playwright, str, str], Awaitable[None]]
