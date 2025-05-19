import random

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
)
from pydantic import BaseModel, PrivateAttr

from broker_agent.config.logging import get_logger
from broker_agent.config.settings import config

logger = get_logger(__name__)


class ScrapingBrowser(BaseModel):
    """Manages a Playwright browser instance for scraping."""

    _playwright: Playwright = PrivateAttr()
    _user_agent: str = PrivateAttr()
    _browser: Browser | None = PrivateAttr(default=None)
    _context: BrowserContext | None = PrivateAttr(default=None)
    _page: Page | None = PrivateAttr(default=None)

    def __init__(self, playwright: Playwright, user_agent: str, **data):
        super().__init__(**data)
        self._playwright = playwright
        self._user_agent = user_agent
        self._browser = None
        self._context = None
        self._page = None

    async def _get_browser_context_config(self) -> dict:
        """Helper to generate browser context configuration."""
        viewport = random.choice(config.browser_settings.viewport_sizes)
        timezone_id = random.choice(config.browser_settings.timezones)
        return {
            "user_agent": self._user_agent,
            "viewport": viewport,
            "locale": "en-US",
            "timezone_id": timezone_id,
            "device_scale_factor": random.choice([1, 2]),
            "has_touch": random.choice([True, False]),
            "permissions": ["geolocation"],
            "java_script_enabled": True,
            "bypass_csp": True,
        }

    async def __aenter__(self) -> Page:
        """
        Initializes the browser, context, and page using the browser via BROWSER_API_ENDPOINT.
        """
        try:
            self._browser = await self._playwright.chromium.connect_over_cdp(
                config.BROWSER_API_ENDPOINT
            )

            # context_config = await self._get_browser_context_config()
            # self._context = await self._browser.new_context(**context_config)
            self._context = await self._browser.new_context()
            await self._context.route("**/*", lambda route: route.continue_())
            self._page = await self._context.new_page()
            return self._page
        except Exception as e:
            # Clean up context if it was partially created
            if self._context:
                try:
                    await self._context.close()
                except Exception:
                    pass
            if self._browser:
                await self._browser.close()
            raise RuntimeError(f"Could not start browser context. Error: {e}") from e

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Closes the browser."""
        if self._browser:
            await self._browser.close()

    @property
    def page(self) -> Page | None:
        return self._page

    @property
    def context(self) -> BrowserContext | None:
        return self._context

    @property
    def browser(self) -> Browser | None:
        return self._browser
