import uuid

from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import UUID

from database.models import Base


class Apartment(Base):
    __tablename__ = "apartments"

    apartment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    link = Column(Text, nullable=False)
