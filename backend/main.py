import os
from datetime import datetime, timedelta, date # !! IMPORTED 'date' !!
from typing import List, Optional
import asyncio 
import json
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Query, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import text

# Import for Web Scraping
from bs4 import BeautifulSoup 

from . import config, database, models, schemas, crud, auth
from fastapi.responses import StreamingResponse
from io import BytesIO
import google.generativeai as genai
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from groq import Groq
from apscheduler.schedulers.background import BackgroundScheduler
from . import alerter


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

# --- API Endpoints ---
# (All your user, token, search history, and watchlist endpoints are unchanged)

@app.post("/api/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)

@app.post("/api/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
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

@app.post("/api/searches/", response_model=schemas.Search)
def create_search_for_user(
    search: schemas.SearchCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    return crud.create_user_search(db=db, search=search, user_id=current_user.id)

@app.get("/api/searches/", response_model=list[schemas.Search])
def read_user_searches(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    searches = crud.get_searches_by_user(db, user_id=current_user.id, skip=skip, limit=limit)
    return searches

@app.get("/api/watchlist/", response_model=list[schemas.WatchlistItem])
def read_watchlist(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    return crud.get_watchlist_items_by_user(db=db, user_id=current_user.id)

@app.post("/api/watchlist/", response_model=schemas.WatchlistItem)
def add_to_watchlist(
    item: schemas.WatchlistItemCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    return crud.create_watchlist_item(db=db, item=item, user_id=current_user.id)

@app.get("/api/notifications/", response_model=list[schemas.Notification])
def read_notifications(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    return crud.get_notifications_by_user(db=db, user_id=current_user.id)

@app.post("/api/notifications/read")
def mark_all_as_read(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    return crud.mark_notifications_as_read(db=db, user_id=current_user.id)

@app.delete("/api/watchlist/{item_id}", response_model=schemas.WatchlistItem)
def remove_from_watchlist(
    item_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    deleted_item = crud.delete_watchlist_item(db=db, item_id=item_id, user_id=current_user.id)
    if deleted_item is None:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    return deleted_item

@app.get("/api/health")
def health_check(db: Session = Depends(database.get_db)):
    try:
        db.execute(text('SELECT 1'))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {e}")

# ===================================================================
# ===== 2. HEALTH CANADA WEB SCRAPING FUNCTION (Unchanged)
# ===================================================================
async def search_health_canada(q: str, client: httpx.AsyncClient) -> List[dict]:
    """
    Searches Health Canada by SCRAPING the HTML results page.
    This version uses the exact HTML tags you found by inspecting.
    """
    print("\n" + "="*50)
    print(f"--- [HEALTH CANADA] STARTING WEB SCRAPE FOR: {q} ---")
    print("="*50)
    
    try:
        scrape_url = f"https://recalls-rappels.canada.ca/en/search/site?search_api_fulltext={q}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
        }
        
        print(f"[HEALTH CANADA] Scraping URL: {scrape_url}")
        
        response = await client.get(scrape_url, timeout=30.0, headers=headers, follow_redirects=True)
        response.raise_for_status()
        
        print("[HEALTH CANADA] Page downloaded. Parsing HTML...")
        
        soup = BeautifulSoup(response.text, "lxml")
        
        search_results = soup.find_all("div", class_="views-row")
        
        print(f"[HEALTH CANADA] Found {len(search_results)} HTML blocks.")
        
        results = []
        
        for item in search_results:
            try:
                # 1. Find Title
                title_span = item.find("span", class_="homepage-recent")
                if not title_span:
                    continue 
                
                title_tag = title_span.find("a")
                if not title_tag:
                    continue 
                
                title = title_tag.text.strip()
                source_url = "https://recalls-rappels.canada.ca" + title_tag["href"]

                # 2. Find Date
                date_span = item.find("span", class_="ar-type")
                if not date_span:
                    continue 
                
                date_text_parts = date_span.text.split('|')
                date = date_text_parts[-1].strip() if len(date_text_parts) > 1 else "Unknown Date"

                # 3. Find Description
                problem_tag = item.find("div", class_="field-name-field-problem")
                description = problem_tag.find("p").text.strip() if problem_tag else "" # !! Set to "" instead of "No description"
                
                # 4. Guess Severity
                severity = 'low'
                if "Type I" in title:
                    severity = 'high'
                elif "Type II" in title:
                    severity = 'medium'

                alert = {
                    'title': title,
                    'description': description,
                    'date': date,
                    'source': 'Health Canada',
                    'severity': severity,
                    'source_url': source_url,
                    'recall_number': "N/A (Scraped)",
                    'event_id': "N/A (Scraped)"
                }
                results.append(alert)
            
            except Exception as e:
                print(f"[HEALTH CANADA] Error parsing one item (skipping): {e}")
        
        print(f"[HEALTH CANADA] Finished scraping. Found {len(results)} health product matches.")
        print("="*50 + "\n")
        return results
        
    except Exception as e:
        print("\n" + "!"*50)
        print(f"[HEALTH CANADA] !!! CRITICAL SCRAPING ERROR !!!")
        print(f"[HEALTH CANADA] Error Type: {type(e)}")
        print(f"[HEALTH CANADA] Error Details: {str(e)}")
        print("!"*50 + "\n")
        return []

#3. FDA SEARCH FUNCTION
async def search_fda(q: str, client: httpx.AsyncClient) -> List[dict]:
    """
    Searches the openFDA API for drug enforcement reports.
    """
    try:
        start_str, end_str = get_date_range()
        api_url = f"https://api.fda.gov/drug/enforcement.json?search=report_date:[{start_str}+TO+{end_str}]+AND+(product_description:{q}+OR+reason_for_recall:{q})&limit=100"
        
        response = await client.get(api_url)
        response.raise_for_status()
        data = response.json()

        results = []
        for recall in data.get('results', []):
            event_id = recall.get('event_id')
            recall_number = recall.get('recall_number')
            
            # FIXED: Correct URL format for FDA Enforcement Reports
            # The FDA uses their new enforcement report system at cacmap.fda.gov
            # You can link to either the event or search by recall number
            if recall_number:
                # Option 1: Search by recall number (most reliable)
                source_url = f"https://cacmap.fda.gov/safety/recalls-market-withdrawals-safety-alerts/enforcement-reports?search={recall_number}"
            elif event_id:
                # Option 2: If no recall number, try event ID search
                source_url = f"https://cacmap.fda.gov/safety/recalls-market-withdrawals-safety-alerts/enforcement-reports?event_id={event_id}"
            else:
                # Option 3: Fallback to general enforcement reports page
                source_url = "https://cacmap.fda.gov/safety/recalls-market-withdrawals-safety-alerts/enforcement-reports"

            # Date formatting
            date_str = recall.get('recall_initiation_date', '')
            formatted_date = date_str
            if len(date_str) == 8:
                try:
                    formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
                except Exception:
                    formatted_date = date_str

            alert = {
                'title': recall.get('product_description', 'No Title').split('.')[0],
                'description': recall.get('reason_for_recall', ''),
                'date': formatted_date,
                'source': 'FDA',
                'severity': get_severity(recall.get('classification', '')),
                'source_url': source_url,
                'recall_number': recall_number,
                'event_id': event_id
            }
            results.append(alert)
        return results

    except httpx.HTTPStatusError as e:
        print(f"[FDA API ERROR]: {e.response.text}")
        return []
    except Exception as e:
        print(f"[FDA UNKNOWN ERROR]: {str(e)}")
        return []
# ===================================================================
# ===== 4. MAIN SEARCH ENDPOINT (!! FILTERS ADDED !!)
# ===================================================================
@app.get("/api/search")
async def search_drugs(
    q: str = Query(..., min_length=2, description="The search query for drugs or recalls."),
    # !! NEW FILTER PARAMETERS WITH DEFAULTS !!
    date_filter: str = "all",
    source_filter: str = "all",
    severity_filter: str = "all",
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Searches FDA AND Health Canada, then applies filters.
    """
    if not q:
        return {"results": [], "total": 0}

    async with httpx.AsyncClient() as client:
        try:
            (fda_results, canada_results) = await asyncio.gather(
                search_fda(q, client),
                search_health_canada(q, client)
            )

            all_results = fda_results + canada_results
            
            # --- !! START NEW FILTER LOGIC !! ---

            # 1. Date Filter
            if date_filter != "all":
                today = date.today()
                cutoff_date = None
                if date_filter == "1y":
                    cutoff_date = today - timedelta(days=365)
                elif date_filter == "3y":
                    cutoff_date = today - timedelta(days=365 * 3)
                elif date_filter == "5y":
                    cutoff_date = today - timedelta(days=365 * 5)
                
                if cutoff_date:
                    filtered_list = []
                    for alert in all_results:
                        try:
                            # Convert "YYYY-MM-DD" string to a date object
                            alert_date = datetime.strptime(alert.get('date', ''), "%Y-%m-%d").date()
                            if alert_date >= cutoff_date:
                                filtered_list.append(alert)
                        except (ValueError, TypeError):
                            continue # Skip alerts with bad/missing dates
                    all_results = filtered_list

            # 2. Source Filter
            if source_filter != "all":
                all_results = [a for a in all_results if a.get('source') == source_filter]

            # 3. Severity Filter
            if severity_filter != "all":
                all_results = [a for a in all_results if a.get('severity') == severity_filter]
            
            # --- !! END NEW FILTER LOGIC !! ---

            # Sort *after* filtering
            all_results.sort(
                key=lambda x: x.get('date', '1900-01-01'), 
                reverse=True
            )

            return {"results": all_results, "total": len(all_results)}

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")

# ===================================================================
# ===== 5. ALL OTHER FUNCTIONS (Unchanged)
# ===================================================================
groq_client = Groq(api_key=config.GROQ_API_KEY)

def generate_summary_with_groq(query: str, alerts: list[schemas.AlertItem]):
    alert_details = "\n".join([
        # !! Use title as description, since description is hidden !!
        f"- Date: {a.date}, Severity: {a.severity.upper()}, Title: {a.title[:200]}..."
        for a in alerts
    ])

    prompt = f"""
    As a pharmaceutical compliance analyst, provide a concise, professional executive summary
    for a report on the component "{query}". The key findings from enforcement reports are listed below.
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

    
    story.append(Paragraph(f"Compliance Report: {query}", styles['h1']))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Generated for: {current_user.email}", styles['Normal']))
    story.append(Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d')}", styles['Normal']))
    story.append(Spacer(1, 24))

    story.append(Paragraph("Executive Summary", styles['h2']))
    story.append(Paragraph(summary, styles['BodyText']))
    story.append(Spacer(1, 24))

    
    story.append(Paragraph("Detailed Alerts", styles['h2']))
    # !! Use Title instead of Description in report !!
    table_data = [['Date', 'Severity', 'Title']]
    for alert in alerts:
        table_data.append([
            alert.date,
            alert.severity.upper(),
            Paragraph(alert.title, styles['BodyText']) # !! Changed from description
        ])

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

    # !! Use Title as context, since description is hidden/empty !!
    context = "\n\n".join([
        f"Document Title: {a.title}\nContent: {a.title}"
        for a in alerts
    ])

    prompt = f"""
    You are a helpful pharmaceutical compliance assistant.
    Based ONLY on the context documents provided below, answer the user's question.
    The context for each document is its Title.
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
    

def get_date_range():
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180) # Keeping the 180-day range for FDA
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
scheduler.add_job(alerter.check_for_new_reports, 'interval', hours=24)
scheduler.start()