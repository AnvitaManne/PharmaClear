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
from fastapi.responses import StreamingResponse
from io import BytesIO
import google.generativeai as genai
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from groq import Groq
# backend/main.py (add to imports)
from apscheduler.schedulers.background import BackgroundScheduler
from . import alerter


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

@app.get("/api/watchlist/", response_model=list[schemas.WatchlistItem])
def read_watchlist(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Retrieves the watchlist for the currently logged-in user.
    """
    return crud.get_watchlist_items_by_user(db=db, user_id=current_user.id)


@app.post("/api/watchlist/", response_model=schemas.WatchlistItem)
def add_to_watchlist(
    item: schemas.WatchlistItemCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Adds a new item to the user's watchlist.
    """
    return crud.create_watchlist_item(db=db, item=item, user_id=current_user.id)
@app.get("/api/notifications/", response_model=list[schemas.Notification])
def read_notifications(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Retrieves all notifications for the currently logged-in user.
    """
    return crud.get_notifications_by_user(db=db, user_id=current_user.id)


@app.post("/api/notifications/read")
def mark_all_as_read(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Marks all of the user's unread notifications as read.
    """
    return crud.mark_notifications_as_read(db=db, user_id=current_user.id)


@app.delete("/api/watchlist/{item_id}", response_model=schemas.WatchlistItem)
def remove_from_watchlist(
    item_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Deletes an item from the user's watchlist.
    """
    deleted_item = crud.delete_watchlist_item(db=db, item_id=item_id, user_id=current_user.id)
    if deleted_item is None:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    return deleted_item

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
                event_id = recall.get('event_id')
                recall_number = recall.get('recall_number')
                source_url = f"https://www.accessdata.fda.gov/scripts/ires/index.cfm?Event_ID_Search={event_id}" if event_id else None

                alert = {
                    'title': recall.get('product_description', 'No Title').split('.')[0],
                    'description': recall.get('reason_for_recall', 'No Description'),
                    'date': recall.get('recall_initiation_date', ''),
                    'source': 'FDA',
                    'severity': get_severity(recall.get('classification', '')),
                    'source_url': source_url,
                    # --- ADDING DEBUG INFO ---
                    'recall_number': recall_number,
                    'event_id': event_id
                }
                results.append(alert)

            return {"results": results, "total": len(results)}

        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Error from FDA API: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")

# Configure Google AI client
groq_client = Groq(api_key=config.GROQ_API_KEY)

def generate_summary_with_groq(query: str, alerts: list[schemas.AlertItem]):
    alert_details = "\n".join([
        f"- Date: {a.date}, Severity: {a.severity.upper()}, Description: {a.description[:200]}..."
        for a in alerts
    ])

    prompt = f"""
    As a pharmaceutical compliance analyst, provide a concise, professional executive summary
    for a report on the component "{query}". The key findings from FDA enforcement reports are listed below.
    Highlight critical patterns, high-severity recalls, and the overall risk profile based on this data.

    Key Findings:
    {alert_details}

    Executive Summary (2-3 paragraphs):
    """

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            # Llama3 8b is extremely fast and great for summarization
            model="llama-3.1-8b-instant", 
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"Groq API error: {e}")
        return "Summary could not be generated due to an API error."


@app.post("/api/report")
def generate_report(
    report_data: schemas.ReportRequest,
    current_user: models.User = Depends(auth.get_current_user)
):
    query = report_data.query
    alerts = report_data.alerts

    summary = generate_summary_with_groq(query, alerts)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Title and metadata
    story.append(Paragraph(f"Compliance Report: {query}", styles['h1']))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Generated for: {current_user.email}", styles['Normal']))
    story.append(Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d')}", styles['Normal']))
    story.append(Spacer(1, 24))

    # AI-generated Executive Summary
    story.append(Paragraph("Executive Summary", styles['h2']))
    story.append(Paragraph(summary, styles['BodyText']))
    story.append(Spacer(1, 24))

    # Detailed Alerts Table
    story.append(Paragraph("Detailed Alerts", styles['h2']))
    table_data = [['Date', 'Severity', 'Description']]
    for alert in alerts:
        # Wrap long descriptions in a Paragraph for proper table cell rendering
        table_data.append([
            alert.date,
            alert.severity.upper(),
            Paragraph(alert.description, styles['BodyText'])
        ])

    # Define table with column widths
    table = Table(table_data, colWidths=[70, 70, 340])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(table)

    doc.build(story)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type='application/pdf',
        headers={'Content-Disposition': f'attachment; filename="{query}-report.pdf"'}
    )

# backend/main.py (add this endpoint)

@app.post("/api/chat", response_model=schemas.ChatResponse)
def chat_with_results(
    chat_request: schemas.ChatRequest,
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Answers a user's question based on the context of their search results (RAG).
    """
    question = chat_request.question
    alerts = chat_request.context_alerts

    # RAG Step 1: Format the retrieved context
    context = "\n\n".join([
        f"Document Title: {a.description[:80]}...\nContent: {a.description}"
        for a in alerts
    ])

    # RAG Step 2: Augment the prompt with the context
    prompt = f"""
    You are a helpful pharmaceutical compliance assistant.
    Based ONLY on the context documents provided below, answer the user's question.
    If the answer is not found in the context, say "I cannot answer that based on the provided results."

    CONTEXT DOCUMENTS:
    ---
    {context}
    ---

    USER'S QUESTION:
    {question}

    ANSWER:
    """

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.1-8b-instant",
        )
        answer = chat_completion.choices[0].message.content
        return schemas.ChatResponse(answer=answer)
    except Exception as e:
        print(f"Groq RAG error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get an answer from the AI.")
    

# --- Helper Functions ---
def get_date_range():
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    start_str = start_date.strftime('%Y%m%d')
    end_str = end_date.strftime('%Y%m%d')
    return start_str, end_str

def get_severity(classification: str = '') -> str:
    if not classification:
        return 'low'
    if classification=="Class I":
        return 'high'
    elif classification=="Class II":
        return 'medium'
    return 'low'
print("--- SCHEDULER: Initializing and starting background alerter... ---") 
scheduler = BackgroundScheduler()
# For testing, run every 30 seconds. For production, you'd use 'hours=24' or similar.
scheduler.add_job(alerter.check_for_new_reports, 'interval',hours=24)
scheduler.start()