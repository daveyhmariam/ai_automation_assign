import os
import datetime
import logging
import json
import firebase_admin
from firebase_functions import https_fn
from firebase_admin import initialize_app
import google.generativeai as genai
from common.utils import send_gmail, get_from_storage, save_to_storage, get_sheets_service
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
if not firebase_admin._apps:
    firebase_admin.initialize_app()

GENAI_API_KEY = os.environ.get("GEMINI_API_KEY")
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID")
BUCKET_NAME = os.environ.get("FIREBASE_STORAGE_BUCKET", "ai-support-agent-f1902.appspot.com")
genai.configure(api_key=GENAI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

@https_fn.on_request()
def chat_processor(req: https_fn.Request) -> https_fn.Response:
    headers = {
        "Access-Control-Allow-Origin": "http://localhost:5000",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    }
    
    if req.method == "OPTIONS":
        return https_fn.Response(status=204, headers=headers)

    try:
        data = req.get_json()
        customer_email = data.get("email", "").strip()
        message = data.get("message", "").strip()
        logging.info(f"Received chat from {customer_email}: {message}")
        if not customer_email or not message:
            raise ValueError("Email or message missing.")
    except Exception as e:
        logging.error(f"Error parsing request: {e}")
        return https_fn.Response(f"Error: {e}", status=400, headers=headers)

    try:
        prompt = (
            f"Analyze the following chat message:\nMessage: {message}\n\n"
            "1. Determine if the message is a tech support question (e.g., related to account issues, billing, bugs, or technical problems).\n"
            "2. If it is NOT a tech support question, return only:\n"
            "Classification: Non-Tech-Support\nSummary: The query is not related to tech support.\nResponse: Sorry, this query is outside the scope of tech support. Please ask about account issues, billing, or technical problems.\n"
            "3. If it IS a tech support question, provide:\n"
            "- Classification: <type, e.g., 'Billing', 'Bug Report', 'General Inquiry'>\n"
            "- Summary: <one sentence summarizing the issue>\n"
            "- Response: <helpful tech support response>\n"
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

        # If non-tech-support, skip storage, ticket creation, and email
        if classification == "Non-Tech-Support":
            return https_fn.Response(json.dumps({"response": support_response}), status=200, headers=headers)
    except Exception as e:
        logging.error(f"Error from Gemini API: {e}")
        return https_fn.Response(f"Error: {e}", status=500, headers=headers)

    try:
        # Save to Firebase Storage
        file_path = f"chat_history/{customer_email}.json"
        chat_history = get_from_storage(BUCKET_NAME, file_path)
        ticket_id = str(int(datetime.datetime.now().timestamp()))
        chat_entry = {
            "ticket_id": ticket_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "email": customer_email,
            "message": message,
            "summary": summary,
            "classification": classification,
            "status": "Open",
            "response": support_response
        }
        chat_history.append(chat_entry)
        save_to_storage(BUCKET_NAME, file_path, chat_history)
        logging.info(f"Chat stored for {customer_email}, ticket {ticket_id}")
    except Exception as e:
        logging.error(f"Error storing chat history: {e}")
        return https_fn.Response(f"Error: {e}", status=500, headers=headers)

    try:
        # Create ticket in Google Sheets
        sheet = get_sheets_service().spreadsheets()
        values = [[
            ticket_id,
            datetime.datetime.now().isoformat(),
            customer_email,
            "Chat Support Request",
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
        logging.info(f"Ticket {ticket_id} created in Google Sheets for {customer_email}")
    except Exception as e:
        logging.error(f"Error creating ticket in Google Sheets: {e}")
        return https_fn.Response(f"Error: {e}", status=500, headers=headers)

    try:
        send_gmail(customer_email, f"Re: Support Chat", support_response)
        logging.info(f"Email sent to {customer_email}")
    except Exception as e:
        logging.error(f"Error sending email: {e}")
        return https_fn.Response(f"Error: {e}", status=500, headers=headers)

    return https_fn.Response(json.dumps({"response": support_response}), status=200, headers=headers)

@https_fn.on_request()
def get_chat_history(req: https_fn.Request) -> https_fn.Response:
    headers = {
        "Access-Control-Allow-Origin": "http://localhost:5000",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    }
    
    if req.method == "OPTIONS":
        return https_fn.Response(status=204, headers=headers)

    try:
        data = req.get_json()
        customer_email = data.get("email", "").strip()
        if not customer_email:
            raise ValueError("Email missing")
        file_path = f"chat_history/{customer_email}.json"
        history = get_from_storage(BUCKET_NAME, file_path)
        return https_fn.Response(json.dumps(history), status=200, headers=headers)
    except Exception as e:
        logging.error(f"Error fetching chat history: {e}")
        return https_fn.Response(f"Error: {e}", status=500, headers=headers)