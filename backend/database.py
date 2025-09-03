# backend/database.py (Corrected)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Import our configuration
from .config import DATABASE_URL

# The 'engine' is the core interface to the database.
# It now uses the URL from our config file.
engine = create_engine(DATABASE_URL)

# A 'SessionLocal' class will be used to create individual database sessions (connections).
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 'Base' is a class that our database model classes will inherit from.
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()