import re
from datetime import datetime

from playwright.async_api import Page
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from broker_agent.browser.utils import get_text_content_with_timeout
from database.alembic.models.models import Apartment


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


async def save_listings_to_db(listings: list[dict[str, any]], session: AsyncSession):
    """
    Save apartment listings to the database.

    Args:
        listings: List of listing details to save
        Session: SQLAlchemy sessionmaker
    """
    # Use a with block to manage the session lifecycle
    for listing in listings:
        try:
            # Check if the apartment already exists
            if not _apartment_exists(session, listing):
                # Process and add the apartment
                _process_and_add_apartment(session, listing)
        except IntegrityError as conflict_error:
            session.rollback()  # Roll back just this record
            print(
                f"Warning: Conflict or unique violation for listing {listing}: {conflict_error}"
            )
            continue  # Continue with the next listing
        except Exception as e:
            print(
                f"Warning: Error processing listing {listing['link'] if 'link' in listing else 'unknown'}: {e}"
            )
            continue  # Continue with the next listing

    # Commit the session at the end
    _commit_session(session)


def _apartment_exists(db_session, listing: dict[str, any]) -> bool:
    """
    Check if an apartment with the given link already exists in the database.

    Args:
        db_session: SQLAlchemy session
        listing: Apartment listing data

    Returns:
        True if apartment exists, False otherwise
    """
    existing_apartment = (
        db_session.query(Apartment).filter_by(link=listing["link"]).first()
    )
    return existing_apartment is not None


def _process_and_add_apartment(db_session, listing: dict[str, any]) -> None:
    """
    Process listing data and add a new apartment to the database.

    Args:
        db_session: SQLAlchemy session
        listing: Apartment listing data
    """
    days_on_market = _extract_days_on_market(listing)
    available_date = _parse_available_date(listing)
    price = _parse_price(listing)

    # Create a new apartment record with extracted details
    new_apartment = Apartment(
        name=listing["name"],
        price=price,
        description=listing["description"],
        available_date=available_date,
        days_on_market=days_on_market,
        link=listing["link"],
        image_urls=[],  # TODO: Add image urls
    )
    db_session.add(new_apartment)
    db_session.flush()


def _extract_days_on_market(listing: dict[str, any]) -> int:
    """
    Extract days on market from listing data.

    Args:
        listing: Apartment listing data

    Returns:
        Number of days on market as integer
    """
    days_on_market = 0
    try:
        if isinstance(listing["days_on_market"], str):
            # Extract numeric value from string like "Days on market50 days"
            days_match = re.search(r"(\d+)", listing["days_on_market"])
            if days_match:
                days_on_market = int(days_match.group(1))
    except Exception as e:
        print(
            f"Warning: Could not parse days_on_market from {listing['days_on_market']}: {e}"
        )
    return days_on_market


def _parse_available_date(listing: dict[str, any]) -> datetime:
    """
    Parse available date from listing data.

    Args:
        listing: Apartment listing data

    Returns:
        Available date as datetime object
    """
    available_date = datetime.now()
    try:
        if isinstance(listing["available_date"], str):
            if "Available now" in listing["available_date"]:
                available_date = datetime.now()
            else:
                # Try to extract date if in standard format
                available_date = datetime.strptime(
                    listing["available_date"], "%Y-%m-%d"
                )
    except Exception as e:
        print(
            f"Warning: Could not parse available_date from {listing['available_date']}: {e}"
        )
    return available_date


def _parse_price(listing: dict[str, any]) -> float:
    """
    Parse price from listing data.

    Args:
        listing: Apartment listing data

    Returns:
        Price as float
    """
    price = 0
    try:
        if isinstance(listing["price"], str):
            # Extract the first price value (e.g., $3,146)
            price_match = re.search(r"\$([0-9,]+)", listing["price"])
            if price_match:
                # Remove commas and convert to float
                price = float(price_match.group(1).replace(",", ""))
        elif isinstance(listing["price"], int | float):
            price = float(listing["price"])
    except Exception as e:
        print(f"Warning: Could not parse price from {listing['price']}: {e}")
    return price


def _commit_session(db_session) -> None:
    """
    Commit the database session and handle any errors.

    Args:
        db_session: SQLAlchemy session
    """
    try:
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        print(f"Error committing to database: {e}")
