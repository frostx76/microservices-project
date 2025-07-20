from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class Review(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    film_id: int = Field(index=True)
    user_id: int = Field(index=True)
    text: str = Field(min_length=10, max_length=2000)
    rating: int = Field(ge=1, le=10)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_approved: bool = Field(default=False)