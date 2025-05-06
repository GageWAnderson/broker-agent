import uuid
from datetime import datetime

from sqlalchemy import ARRAY, Column, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Apartment(Base):
    __tablename__ = "apartments"

    apartment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date_scraped = Column(DateTime, nullable=False, default=datetime.now)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    available_date = Column(DateTime, nullable=False)
    days_on_market = Column(Integer, nullable=False)
    link = Column(Text, nullable=False, unique=True)
    image_urls = Column(ARRAY(Text), nullable=False)
