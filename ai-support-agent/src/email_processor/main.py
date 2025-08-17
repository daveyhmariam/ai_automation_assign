import os
import datetime
import logging
import firebase_admin
from firebase_functions import https_fn
from firebase_admin import initialize_app
import google.generativeai as genai
from common.utils import get_sheets_service, send_gmail
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Initialize Firebase App
if not firebase_admin._apps:
    firebase_admin.initialize_app()

# API Keys from environment variables
GENAI_API_KEY = os.environ.get("GEMINI_API_KEY")
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID")

# Initialize Gemini API client
genai.configure(api_key=GENAI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

@https_fn.on_request()
def email_processor(req: https_fn.Request) -> https_fn.Response:
    try:
        data = req.get_json()
        subject = data.get("subject", "").strip()
        body = (data.get("html") or data.get("text") or "").strip()

        # Ensure customer_email is always a plain string email
        customer_email = ""
        if "from" in data and isinstance(data["from"], dict):
            customer_email = str(data["from"].get("email", "")).strip()

        logging.info(f"Received email from {customer_email} with subject: {subject}")

        if not customer_email:
            raise ValueError("Customer email is missing.")
    except Exception as e:
        logging.error(f"Error parsing request: {e}")
        return https_fn.Response(f"Error parsing request: {e}", status=400)

    try:
        # Ask AI for classification, summary, and tech support suggestion
        prompt = (
            f"Analyze the following email:\nSubject: {subject}\nBody: {body}\n\n"
            "1. Classify the issue (e.g., 'Billing', 'Bug Report', 'General Inquiry').\n"
            "2. Provide a one-sentence summary.\n"
            "3. Suggest a helpful tech support response for the user.\n"
            "Return in the format:\nClassification: <type>\nSummary: <one sentence>\nResponse: <helpful text>"
        )
        gemini_response = model.generate_content(prompt)
        ai_text = gemini_response.text.strip()
        logging.info(f"AI output:\n{ai_text}")

        classification, summary, support_response = "General Inquiry", "", ""
        for line in ai_text.split("\n"):
            if line.startswith("Classification:"):
                classification = line.replace("Classification:", "").strip()
            elif line.startswith("Summary:"):
                summary = line.replace("Summary:", "").strip()
            elif line.startswith("Response:"):
                support_response = line.replace("Response:", "").strip()
    except Exception as e:
        logging.error(f"Error from Gemini API: {e}")
        return https_fn.Response(f"Error from Gemini API: {e}", status=500)

    try:
        # Check for existing open ticket
        sheet = get_sheets_service().spreadsheets()
        result = sheet.values().get(
            spreadsheetId=GOOGLE_SHEET_ID,
            range="prepare me the spread sheet!A2:H"
        ).execute()
        rows = result.get("values", [])

        existing_ticket_row = None
        for idx, row in enumerate(rows):
            if len(row) >= 7 and row[2] == customer_email and row[3] == subject and row[6] == "Open":
                existing_ticket_row = idx + 2
                break

        if existing_ticket_row:
            # Update existing ticket
            logging.info(f"Updating existing ticket at row {existing_ticket_row}")
            update_values = [[
                datetime.datetime.now().isoformat(),
                customer_email,
                subject,
                summary,
                classification
            ]]
            sheet.values().update(
                spreadsheetId=GOOGLE_SHEET_ID,
                range=f"prepare me the spread sheet!B{existing_ticket_row}:F{existing_ticket_row}",
                valueInputOption="RAW",
                body={"values": update_values}
            ).execute()
            ticket_id = rows[existing_ticket_row - 2][0]
        else:
            # Append new ticket
            ticket_id = str(int(datetime.datetime.now().timestamp()))
            values = [[
                ticket_id,
                datetime.datetime.now().isoformat(),
                customer_email,
                subject,
                summary,
                classification,
                "Open",
                ""
            ]]
            sheet.values().append(
                spreadsheetId=GOOGLE_SHEET_ID,
                range="prepare me the spread sheet!A2:H",
                valueInputOption="RAW",
                body={"values": values}
            ).execute()

    except Exception as e:
        logging.error(f"Error writing to Google Sheets: {e}")
        return https_fn.Response(f"Error writing to Google Sheets: {e}", status=500)

    try:
        # Send AI tech support response via Gmail
        send_gmail(customer_email, f"Re: {subject}", support_response)
        logging.info(f"Email sent to {customer_email}")
    except Exception as e:
        logging.error(f"Error sending email with SMTP: {e}")
        return https_fn.Response(f"Error sending email with SMTP: {e}", status=500)

    logging.info("Ticket processed successfully!")
    return https_fn.Response("Ticket processed successfully!", status=200)