import os
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import smtplib
from email.mime.text import MIMEText

def get_sheets_service():
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    SERVICE_ACCOUNT_FILE = os.environ.get("SERVICE_ACCOUNT_FILE", "config/credentials.json")
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('sheets', 'v4', credentials=creds)

def send_gmail(to_email, subject, body_text):
    sender_email = os.environ.get("GMAIL_SENDER_EMAIL", "daveyhmariam+support@gmail.com")
    auth_email = os.environ.get("GMAIL_AUTH_EMAIL", "daveyhmariam@gmail.com")
    app_password = os.environ.get("GMAIL_APP_PASSWORD")

    if not app_password:
        raise ValueError("GMAIL_APP_PASSWORD not set in .env")

    message = MIMEText(body_text)
    message['to'] = to_email
    message['from'] = sender_email
    message['subject'] = subject

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(auth_email, app_password)
            server.send_message(message)
    except smtplib.SMTPAuthenticationError as e:
        raise Exception(f"Authentication failed: {e}. Check GMAIL_AUTH_EMAIL and GMAIL_APP_PASSWORD.")
    except Exception as e:
        raise Exception(f"Error sending email: {e}")