from sqlalchemy.orm import Session
from . import models, schemas, security

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = security.get_password_hash(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email=email)
    if not user:
        return False
    if not security.verify_password(password, user.hashed_password):
        return False
    return user


def get_searches_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Search).filter(models.Search.owner_id == user_id).offset(skip).limit(limit).all()

def create_user_search(db: Session, search: schemas.SearchCreate, user_id: int):
    db_search = models.Search(**search.model_dump(), owner_id=user_id)
    db.add(db_search)
    db.commit()
    db.refresh(db_search)
    return db_search

def get_watchlist_items_by_user(db: Session, user_id: int):
    return db.query(models.WatchlistItem).filter(models.WatchlistItem.owner_id == user_id).all()

def create_watchlist_item(db: Session, item: schemas.WatchlistItemCreate, user_id: int):
    db_item = db.query(models.WatchlistItem).filter(
        models.WatchlistItem.owner_id == user_id,
        models.WatchlistItem.query_text == item.query_text
    ).first()
    if db_item:
        return db_item 

    db_item = models.WatchlistItem(**item.model_dump(), owner_id=user_id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

def delete_watchlist_item(db: Session, item_id: int, user_id: int):
    db_item = db.query(models.WatchlistItem).filter(
        models.WatchlistItem.id == item_id,
        models.WatchlistItem.owner_id == user_id
    ).first()
    if db_item:
        db.delete(db_item)
        db.commit()
        return db_item
    return None

def create_notification(db: Session, user_id: int, message: str):
    """Creates a new notification for a user."""
    db_notification = models.Notification(owner_id=user_id, message=message)
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification

def get_notifications_by_user(db: Session, user_id: int):
    """Gets all notifications for a user, newest first."""
    return db.query(models.Notification).filter(models.Notification.owner_id == user_id).order_by(models.Notification.created_at.desc()).all()

def mark_notifications_as_read(db: Session, user_id: int):
    """Marks all unread notifications for a user as read."""
    db.query(models.Notification).filter(
        models.Notification.owner_id == user_id,
        models.Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"status": "success", "message": "All notifications marked as read."}