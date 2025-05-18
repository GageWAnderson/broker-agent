import uuid
from datetime import datetime

from sqlalchemy import ARRAY, Column, DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Apartment(Base):
    """
    Core data model for apartment data.
    """

    __tablename__ = "apartments"

    apartment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date_scraped = Column(DateTime, nullable=False, default=datetime.now)
    name = Column(Text, nullable=False)
    price = Column(Float, nullable=False)
    description = Column(Text, nullable=False)
    available_date = Column(DateTime, nullable=False)
    days_on_market = Column(Integer, nullable=False)
    link = Column(Text, nullable=False, unique=True)
    image_urls = Column(ARRAY(Text), nullable=False)
    policies = Column(Text, nullable=True)
    home_features = Column(Text, nullable=True)
    ammenities = Column(Text, nullable=True)
    similar_listings = Column(ARRAY(Text), nullable=True)
    ai_summary = Column(Text, nullable=True)
    sqft = Column(Integer, nullable=True)
    num_beds = Column(Integer, nullable=True)
    num_baths = Column(Integer, nullable=True)
    neighborhood = Column(Text, nullable=True)


class PriceHistory(Base):
    """
    Table for price history for each apartment ID.
    """

    __tablename__ = "price_history"

    price_history_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    apartment_id = Column(
        UUID(as_uuid=True), ForeignKey("apartments.apartment_id"), nullable=False
    )
    price = Column(Float, nullable=False)
    date = Column(DateTime, nullable=False)


class ApartmentTag(Base):
    """
    Enum table for possible tags assigned to apartments.
    """

    __tablename__ = "apartment_tags"

    apartment_tag_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False, unique=True)


class ApartmentTagMapping(Base):
    """
    Many to many relationship between apartments and their tags.
    """

    __tablename__ = "apartment_tag_mappings"

    apartment_tag_mapping_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    apartment_id = Column(
        UUID(as_uuid=True), ForeignKey("apartments.apartment_id"), nullable=False
    )
    apartment_tag_id = Column(
        UUID(as_uuid=True),
        ForeignKey("apartment_tags.apartment_tag_id"),
        nullable=False,
    )
