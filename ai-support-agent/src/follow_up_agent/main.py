import os
import datetime
import firebase_admin
from firebase_functions import scheduler_fn
from firebase_admin import initialize_app
from common.utils import get_sheets_service, send_gmail
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Firebase App
if not firebase_admin._apps:
    firebase_admin.initialize_app()

# API Keys from environment variables
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID")

@scheduler_fn.on_schedule(schedule="0 9 * * *")
def follow_up_agent(event: scheduler_fn.ScheduledEvent) -> None:
    try:
        result = get_sheets_service().spreadsheets().values().get(
            spreadsheetId=GOOGLE_SHEET_ID,
            range="prepare me the spread sheet!A2:H"
        ).execute()
        rows = result.get('values', [])
    except Exception as e:
        print(f"Error reading from Google Sheets: {e}")
        return

    for i, row in enumerate(rows):
        if len(row) >= 8 and row[7] == "Open":
            ticket_date = datetime.datetime.fromisoformat(row[1])
            age = datetime.datetime.now() - ticket_date
            if age.days >= 2:
                customer_email = row[2]
                summary = row[5]
                ticket_id = row[0]

                try:
                    send_gmail(customer_email, f"Follow-up: Ticket {ticket_id}", f"Checking on your issue: {summary}. Resolved? Need help?")
                    update_range = f"prepare me the spread sheet!H{i + 2}"
                    update_body = {'values': [['Follow-up Sent']]}
                    get_sheets_service().spreadsheets().values().update(
                        spreadsheetId=GOOGLE_SHEET_ID,
                        range=update_range,
                        valueInputOption="RAW",
                        body=update_body
                    ).execute()
                    print(f"Follow-up for {ticket_id}")
                except Exception as e:
                    print(f"Error sending email for {ticket_id}: {e}")