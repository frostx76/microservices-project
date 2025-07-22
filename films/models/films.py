from sqlmodel import SQLModel, Field


class Film(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    director: str
    year: int = Field(gt=1900)
    rating: float = Field(ge=0, le=10)
