# backend/main.py

import os
from datetime import datetime, timedelta
from typing import List, Optional

import httpx
from fastapi import FastAPI, HTTPException, Query, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import text

# Import our modules, including the 'get_db' function from database.py
from . import config, database, models, schemas, crud, auth

# This line creates the 'users' table in your database if it doesn't exist
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="PharmaClear API",
    description="API for fetching pharmaceutical compliance data.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- The get_db function is now imported from database.py ---
# We no longer define it here.


# --- API Endpoints ---

@app.post("/api/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    """
    Creates a new user in the database.
    """
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)

@app.post("/api/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    """
    Logs in a user and returns a JWT access token.
    """
    user = crud.authenticate_user(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# backend/main.py
# ... (after the /api/token endpoint) ...

@app.post("/api/searches/", response_model=schemas.Search)
def create_search_for_user(
    search: schemas.SearchCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Saves a search query for the currently logged-in user.
    """
    return crud.create_user_search(db=db, search=search, user_id=current_user.id)


@app.get("/api/searches/", response_model=list[schemas.Search])
def read_user_searches(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Retrieves the search history for the currently logged-in user.
    """
    searches = crud.get_searches_by_user(db, user_id=current_user.id, skip=skip, limit=limit)
    return searches

@app.get("/api/health")
def health_check(db: Session = Depends(database.get_db)): # <-- TYPO FIXED HERE
    """
    Checks the database connection.
    """
    try:
        db.execute(text('SELECT 1'))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {e}")

@app.get("/api/search")
async def search_drugs(
    q: str = Query(..., min_length=2, description="The search query for drugs or recalls."),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Searches the openFDA API for drug enforcement reports.
    """
    # ... (rest of the function is correct and remains unchanged) ...
    if not q:
        return {"results": [], "total": 0}
    start_str, end_str = get_date_range()
    async with httpx.AsyncClient() as client:
        try:
            api_url = f"https://api.fda.gov/drug/enforcement.json?search=report_date:[{start_str}+TO+{end_str}]+AND+(product_description:{q}+OR+reason_for_recall:{q})&limit=100"
            response = await client.get(api_url)
            response.raise_for_status()
            data = response.json()
            results = []
            for recall in data.get('results', []):
                alert = {
                    'title': recall.get('product_description', 'No Title').split('.')[0],
                    'description': recall.get('reason_for_recall', 'No Description'),
                    'date': recall.get('recall_initiation_date', ''),
                    'source': 'FDA',
                    'severity': get_severity(recall.get('classification', '')),
                    'components': recall.get('openfda', {}).get('substance_name', []),
                    'source_url': 'https://www.fda.gov/safety/recalls-market-withdrawals-safety-alerts'
                }
                results.append(alert)
            return {"results": results, "total": len(results)}
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Error from FDA API: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")

# --- Helper Functions ---
def get_date_range():
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    start_str = start_date.strftime('%Y%m%d')
    end_str = end_date.strftime('%Y%m%d')
    return start_str, end_str

def get_severity(reason: str = '') -> str:
    if not reason:
        return 'low'
    reason = reason.lower()
    if 'class i' in reason or 'serious' in reason:
        return 'high'
    elif 'class ii' in reason or 'temporary' in reason:
        return 'medium'
    return 'low'
