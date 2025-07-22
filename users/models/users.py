from sqlmodel import SQLModel, Field
from datetime import date

class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)  # id из auth
    email: str = Field(index=True, unique=True)
    full_name: str | None = None
    is_active: bool = True
    bio: str | None = Field(default=None, max_length=500)
    birthdate: date | None = None
    phone_number: str | None = Field(default=None, max_length=20)
    address: str | None = None
