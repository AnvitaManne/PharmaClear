# backend/crud.py
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

# backend/crud.py
# ... (existing functions) ...

def get_searches_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Search).filter(models.Search.owner_id == user_id).offset(skip).limit(limit).all()

def create_user_search(db: Session, search: schemas.SearchCreate, user_id: int):
    db_search = models.Search(**search.model_dump(), owner_id=user_id)
    db.add(db_search)
    db.commit()
    db.refresh(db_search)
    return db_search