import random
import re

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
    scrape_images: bool = True

    def __init__(
        self,
        playwright: Playwright,
        user_agent: str,
        scrape_images: bool = True,
        **data,
    ):
        super().__init__(scrape_images=scrape_images, **data)
        self._playwright = playwright
        self._user_agent = user_agent
        self._browser = None
        self._context = None
        self._page = None

    async def __aenter__(self) -> Page:
        """
        Initializes the browser, context, and page using the browser via BROWSER_API_ENDPOINT.
        """
        try:
            if config.LOCAL_BROWSER:
                proxy_settings = self._get_proxy_settings()
                launch_options = {
                    "headless": config.HEADLESS_BROWSER,
                }
                if proxy_settings:
                    launch_options["proxy"] = proxy_settings

                self._browser = await self._playwright.chromium.launch(**launch_options)
                context_config = await self._get_browser_context_config()
                self._context = await self._browser.new_context(**context_config)
            else:
                self._browser = await self._playwright.chromium.connect_over_cdp(
                    config.BROWSER_API_ENDPOINT
                )
                # For remote browsers, we might not have the same level of control
                # or context config might not be applicable/desired in the same way.
                # If specific context adjustments are needed for remote, they should be handled here.
                self._context = await self._browser.new_context()

            # Route to control resource loading and blocked URLs
            await self._context.route("**/*", self._route_handler)
            self._page = await self._context.new_page()
            return self._page
        except Exception as e:
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

    async def _route_handler(self, route):
        """
        Helper function to handle routing for blocking URLs and controlling resource loading.
        Blocks images, CSS, fonts, and media.
        """
        request_url = route.request.url
        resource_type = route.request.resource_type

        # Block URLs based on patterns
        for pattern in config.browser_settings.blocked_url_patterns:
            if re.match(pattern, request_url):
                await route.abort()
                return

        # Block images, CSS, fonts, and media
        # block_types = {"image", "stylesheet", "font", "media"}
        block_types = {"image"}
        if resource_type in block_types:
            await route.abort()
            return

        await route.continue_()

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

    def _get_proxy_settings(self) -> dict:
        """
        Helper to return proxy settings.
        TODO: Move these proxy details to your application's configuration (e.g., config.proxy_settings)
        """
        if not config.BRD_PROXY_USERNAME or not config.BRD_PROXY_PASSWORD:
            raise ValueError(
                "Proxy username or password is not set in the configuration."
            )

        return {
            "server": config.BRD_SERVER,
            "username": config.BRD_PROXY_USERNAME,
            "password": config.BRD_PROXY_PASSWORD,
        }
