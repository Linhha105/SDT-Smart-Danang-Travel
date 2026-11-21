
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    ForeignKey,
    UniqueConstraint,
    Index
)
from sqlalchemy.orm import relationship

from database.connection import Base


class POI(Base):
    """
    Bảng lưu thông tin địa điểm du lịch.
    """

    __tablename__ = "pois"

    id = Column(Integer, primary_key=True, index=True)

    place_id = Column(String(255), unique=True, nullable=False, index=True)

    name = Column(String(500), nullable=False, index=True)
    name_for_emails = Column(String(500), nullable=True)

    address = Column(Text, nullable=True)
    street = Column(String(255), nullable=True)
    city = Column(String(150), nullable=True)
    county = Column(String(150), nullable=True)
    state = Column(String(150), nullable=True)
    country = Column(String(100), nullable=True)

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    phone = Column(String(100), nullable=True)
    website = Column(Text, nullable=True)
    description = Column(Text, nullable=True)

    google_id = Column(String(255), nullable=True)
    cid = Column(String(100), nullable=True)
    location_link = Column(Text, nullable=True)

    source_file = Column(Text, nullable=True)
    cleaning_action = Column(String(100), nullable=True)
    cleaning_note = Column(Text, nullable=True)

    categories = relationship(
        "POICategory",
        back_populates="poi",
        cascade="all, delete-orphan"
    )

    details = relationship(
        "POIDetail",
        back_populates="poi",
        uselist=False,
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_poi_coordinates", "latitude", "longitude"),
    )


class Category(Base):
    """
    Sáu danh mục chính của hệ thống Smart Tourism.
    """

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)

    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(150), nullable=False)

    pois = relationship(
        "POICategory",
        back_populates="category",
        cascade="all, delete-orphan"
    )


class POICategory(Base):
    """
    Bảng liên kết POI với danh mục chính và phụ.
    """

    __tablename__ = "poi_categories"

    id = Column(Integer, primary_key=True, index=True)

    poi_id = Column(
        Integer,
        ForeignKey("pois.id", ondelete="CASCADE"),
        nullable=False
    )

    category_id = Column(
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False
    )

    is_primary = Column(Integer, nullable=False, default=0)

    poi = relationship("POI", back_populates="categories")
    category = relationship("Category", back_populates="pois")

    __table_args__ = (
        UniqueConstraint(
            "poi_id",
            "category_id",
            name="uq_poi_category"
        ),
    )


class POIDetail(Base):
    """
    Thông tin bổ sung từ Outscraper.
    """

    __tablename__ = "poi_details"

    id = Column(Integer, primary_key=True, index=True)

    poi_id = Column(
        Integer,
        ForeignKey("pois.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    subtype = Column(Text, nullable=True)
    place_type = Column(String(255), nullable=True)

    rating = Column(Float, nullable=True)
    reviews = Column(Integer, nullable=True)

    photos_count = Column(Integer, nullable=True)
    photo = Column(Text, nullable=True)
    street_view = Column(Text, nullable=True)
    logo = Column(Text, nullable=True)

    business_status = Column(String(100), nullable=True)

    working_hours = Column(Text, nullable=True)
    working_hours_csv = Column(Text, nullable=True)

    reviews_per_score = Column(Text, nullable=True)
    popular_times = Column(Text, nullable=True)

    prices = Column(Text, nullable=True)
    range = Column(String(100), nullable=True)

    menu_link = Column(Text, nullable=True)
    reservation_links = Column(Text, nullable=True)
    booking_appointment_link = Column(Text, nullable=True)
    order_links = Column(Text, nullable=True)

    verified = Column(Integer, nullable=True)

    poi = relationship("POI", back_populates="details")
