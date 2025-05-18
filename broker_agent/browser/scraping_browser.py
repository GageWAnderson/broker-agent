import random

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
)
from playwright_stealth import stealth_async

from broker_agent.browser.user_agent_rotator import UserAgentRotator
from broker_agent.config.logging import get_logger
from broker_agent.config.settings import config

logger = get_logger(__name__)


class ScrapingBrowser:
    """Manages a Playwright browser instance for scraping."""

    def __init__(
        self,
        playwright: Playwright,
        user_agent_rotator: UserAgentRotator,
        website_name: str,
    ):
        self._playwright = playwright
        self._user_agent_rotator = user_agent_rotator
        self._website_name = website_name
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    async def _get_browser_context_config(self, user_agent: str) -> dict:
        """Helper to generate browser context configuration."""
        viewport = random.choice(config.browser_settings.viewport_sizes)
        timezone_id = random.choice(config.browser_settings.timezones)
        return {
            "user_agent": user_agent,
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
        """Initializes the browser, context, and page."""
        self._browser = await self._playwright.chromium.launch(
            headless=config.HEADLESS_BROWSER,
            args=config.browser_settings.chrome_args,
            ignore_default_args=["--enable-automation"],
        )

        user_agent = await self._user_agent_rotator.get_next_agent()
        context_config = await self._get_browser_context_config(user_agent)
        self._context = await self._browser.new_context(**context_config)

        await self._context.route("**/*", lambda route: route.continue_())
        self._page = await self._context.new_page()
        logger.info(
            f"[{self._website_name}] Starting scraper in new browser instance with user agent: {user_agent}"
        )
        await stealth_async(self._page)
        logger.info(f"[{self._website_name}] Stealth plugin enabled")
        return self._page

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Closes the browser."""
        if self._browser:
            await self._browser.close()
            logger.info(f"[{self._website_name}] Browser instance closed.")

    @property
    def page(self) -> Page | None:
        return self._page

    @property
    def context(self) -> BrowserContext | None:
        return self._context

    @property
    def browser(self) -> Browser | None:
        return self._browser
