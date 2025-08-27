
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, Text, CheckConstraint, UniqueConstraint, ForeignKey, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime

Base = declarative_base()


class Restaurant(Base):
    __tablename__ = 'restaurants'

    id = Column(Integer, primary_key=True, autoincrement=True)
    notion_id = Column(String, unique=True, nullable=False)

    name = Column(String, nullable=False)
    place_type = Column(String(20))
    city = Column(String)
    yandex_maps_url = Column(String)

    address = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)

    yandex_rating = Column(Float)

    visited = Column(Boolean, default=False)
    my_service_rating = Column(Float, CheckConstraint('my_service_rating >= 1 AND my_service_rating <= 10'))
    my_food_rating = Column(Float, CheckConstraint('my_food_rating >= 1 AND my_food_rating <= 10'))
    my_coffee_rating = Column(Float, CheckConstraint('my_coffee_rating >= 1 AND my_coffee_rating <= 10'))
    my_interior_rating = Column(Float, CheckConstraint('my_interior_rating >= 1 AND my_interior_rating <= 10'))

    tags = Column(ARRAY(String))
    my_comment = Column(Text)

    last_updated = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.UTC))

    yandex_url_status = Column(String(20), default='unknown')  # ok | broken | unreachable | not_found | unknown
    yandex_url_last_checked = Column(DateTime(timezone=True))

    reviews = relationship("Review", back_populates="restaurant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Restaurant(id={self.id}, name='{self.name}', city='{self.city}')>"


class Review(Base):
    __tablename__ = 'reviews'

    id = Column(Integer, primary_key=True, autoincrement=True)
    restaurant_id = Column(Integer, ForeignKey('restaurants.id', ondelete='CASCADE'), nullable=False)
    yandex_review_id = Column(String, nullable=False)

    author_name = Column(String)
    rating = Column(Integer, CheckConstraint('rating >= 1 AND rating <= 5'))
    comment_text = Column(Text)

    processed_verdict = Column(String(100))
    processed_tags = Column(ARRAY(String))
    sentiment_score = Column(Float)

    original_date = Column(DateTime(timezone=True))
    retrieved_date = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)

    restaurant = relationship("Restaurant", back_populates="reviews")

    __table_args__ = (
        UniqueConstraint('restaurant_id', 'yandex_review_id', name='unique_review_per_restaurant'),
    )

    def __repr__(self):
        return f"<Review(id={self.id}, restaurant_id={self.restaurant_id}, rating={self.rating})>"


indexes = [
    'CREATE INDEX idx_reviews_restaurant_id ON reviews(restaurant_id);',
    'CREATE INDEX idx_restaurants_visited ON restaurants(visited);',
    'CREATE INDEX idx_restaurants_city ON restaurants(city);',
    'CREATE INDEX idx_reviews_rating ON reviews(rating);',
    'CREATE INDEX idx_reviews_original_date ON reviews(original_date);',
    'CREATE INDEX idx_restaurants_place_type ON restaurants(place_type);'
]
