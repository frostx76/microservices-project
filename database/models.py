from sqlmodel import SQLModel, Field, Relationship
from datetime import date, datetime
from typing import Optional, List


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    full_name: Optional[str] = None
    bio: Optional[str] = Field(default=None, max_length=500)
    birthdate: Optional[date] = None
    phone_number: Optional[str] = Field(default=None, max_length=20)
    address: Optional[str] = None
    is_active: bool = Field(default=True)

    reviews: List["Review"] = Relationship(back_populates="user")


class Film(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    director: str
    year: int = Field(gt=1900)
    rating: float = Field(ge=0, le=10)

    reviews: List["Review"] = Relationship(back_populates="film")


class Review(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    film_id: int = Field(foreign_key="film.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    text: str = Field(min_length=10, max_length=2000)
    rating: int = Field(ge=1, le=10)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_approved: bool = Field(default=False)

    film: Film = Relationship(back_populates="reviews")
    user: User = Relationship(back_populates="reviews")