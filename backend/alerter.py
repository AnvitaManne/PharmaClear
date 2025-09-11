# backend/alerter.py
from sqlalchemy.orm import Session
import httpx
from datetime import datetime, timedelta

from . import crud, database, models

def get_past_date_str(days: int = 1):
    """Returns a date in the past in YYYYMMDD format for the FDA API."""
    past_date = datetime.now() - timedelta(days=days)
    return past_date.strftime('%Y%m%d')

def check_for_new_reports():
    """
    The main function for the background task.
    Checks for new FDA reports and creates in-app notifications.
    """
    db = database.SessionLocal()
    try:
        print(f"--- [ALERTER] Running daily check at {datetime.now()} ---")

        users_with_watchlist = db.query(models.User).filter(models.User.watchlist_items.any()).all()
        if not users_with_watchlist:
            return

        # For testing, we'll keep looking back 30 days to ensure we find results.
        # For production, this would be set to 1.
        report_date = get_past_date_str(days=30)

        for user in users_with_watchlist:
            for item in user.watchlist_items:
                query = item.query_text
                api_url = f"https://api.fda.gov/drug/enforcement.json?search=report_date:{report_date}+AND+(product_description:{query}+OR+reason_for_recall:{query})&limit=1"

                try:
                    response = httpx.get(api_url)
                    if response.status_code == 200:
                        data = response.json()
                        if 'results' in data and data['results']:
                            # --- CREATE IN-APP NOTIFICATION INSTEAD OF EMAIL ---
                            message = f"New FDA report found for '{query}' on your watchlist."
                            crud.create_notification(db=db, user_id=user.id, message=message)
                            print(f"!!! ALERT !!! Created notification for user {user.email} for query '{query}'.")
                except Exception as api_err:
                    print(f"[ALERTER] Error querying FDA API for '{query}': {api_err}")
    finally:
        db.close()