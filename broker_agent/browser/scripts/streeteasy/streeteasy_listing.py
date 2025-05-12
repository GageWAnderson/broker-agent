from playwright.async_api import Page

from broker_agent.browser.utils import get_text_content_with_timeout


async def scrape_listing_details(page: Page) -> dict[str, any]:
    selectors = {
        "name": '[data-testid="homeAddress"]',
        "price": '[data-testid="priceInfo"]',
        "description": '[data-testid="about-section"]',
        "available_date": '[data-testid="rentalListingSpec-available"]',
        "days_on_market": '[data-testid="rentalListingSpec-daysOnMarket"]',
    }

    apartment_data = {key: None for key in selectors.keys()}

    for field, selector in selectors.items():
        apartment_data[field] = await get_text_content_with_timeout(page, selector)

    return apartment_data
