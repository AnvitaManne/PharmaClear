# backend/security.py
from passlib.context import CryptContext

# Use bcrypt for hashing, which is a standard and secure choice
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)