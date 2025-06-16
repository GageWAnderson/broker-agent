class ScraperAccessDenied(Exception):
    """Custom exception for scraper access denied errors."""

    pass


class PageNavigationLimitReached(Exception):
    """Custom exception for page navigation limit reached errors."""

    pass


class ApartmentScrapingError(Exception):
    """Custom exception for apartment scraping errors."""

    pass
