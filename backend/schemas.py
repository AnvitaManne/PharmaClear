# backend/schemas.py

from pydantic import BaseModel
from datetime import datetime
from typing import Optional
# --- User Schemas ---

# Base attributes for a user
class UserBase(BaseModel):
    email: str

# Attributes required when creating a new user (receives from API)
class UserCreate(UserBase):
    password: str

# Attributes to return when fetching a user (sends back via API)
class User(UserBase):
    id: int
    created_at: datetime

    # This tells Pydantic to read the data even if it's not a dict,
    # but an ORM model (like our SQLAlchemy User model)
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class SearchBase(BaseModel):
    query_text: str

class SearchCreate(SearchBase):
    pass

class Search(SearchBase):
    id: int
    created_at: datetime
    owner_id: int

    class Config:
        from_attributes = True

# We also need to update our User schema to include the searches
class User(UserBase):
    id: int
    created_at: datetime
    searches: list[Search] = [] # <-- ADD THIS LINE

    class Config:
        from_attributes = True