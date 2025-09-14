from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

class SearchBase(BaseModel):
    query_text: str

class SearchCreate(SearchBase):
    pass

class WatchlistItemBase(BaseModel):
    query_text: str

class WatchlistItemCreate(WatchlistItemBase):
    pass

class NotificationBase(BaseModel):
    message: str
    is_read: bool

class Search(SearchBase):
    id: int
    created_at: datetime
    owner_id: int
    class Config:
        from_attributes = True

class WatchlistItem(WatchlistItemBase):
    id: int
    created_at: datetime
    owner_id: int
    class Config:
        from_attributes = True

class Notification(NotificationBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class User(UserBase):
    id: int
    created_at: datetime
    searches: list[Search] = []
    watchlist_items: list[WatchlistItem] = []
    notifications: list[Notification] = []
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class AlertItem(BaseModel):
    date: str
    severity: str
    description: str

class ReportRequest(BaseModel):
    query: str
    alerts: list[AlertItem]

class ChatRequest(BaseModel):
    question: str
    context_alerts: list[AlertItem]

class ChatResponse(BaseModel):
    answer: str