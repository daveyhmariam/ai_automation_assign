# AI-Powered Technical Support Agent

## Overview

An AI-driven system for automating technical support in a SaaS environment, handling chat and email queries, logging tickets in Google Sheets, and sending responses via Gmail SMTP. Built with Firebase (Spark Plan), Gemini AI, Google Sheets API, and Gmail SMTP.

## Installation

1. **Clone the repository**:
   \`\`\`bash
   git clone <repository-url>
   cd ai-support-agent
   \`\`\`

2. **Install Firebase CLI**:
   \`\`\`bash
   npm install -g firebase-tools
   \`\`\`

3. **Set up Python virtual environment**:
   \`\`\`bash
   cd functions
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cd ..
   \`\`\`

4. **Configure environment variables**:
   Create a \`.env\` file in the root directory with:
   \`\`\`
   GEMINI_API_KEY=<your-gemini-key>
   GOOGLE_SHEET_ID=<your-sheet-id>
   GMAIL_AUTH_EMAIL=<your-gmail-email>
   GMAIL_APP_PASSWORD=<your-gmail-app-password>
   FIREBASE_STORAGE_BUCKET=ai-support-agent-f1902.appspot.com
   SERVICE_ACCOUNT_FILE=config/credentials.json
   \`\`\`
   Note: Generate `GMAIL_APP_PASSWORD` via Google Account settings (2-Step Verification enabled). `SERVICE_ACCOUNT_FILE` is a JSON key file for Google Sheets API access.

5. **Start Firebase emulator for local testing**:
   \`\`\`bash
   firebase emulators:start --only functions,hosting
   \`\`\`

   - Access chat UI: `http://localhost:5000/chat.html`
   - Emulator UI: `http://localhost:4000` (for logs and Storage)

6. **Test endpoints locally**:
   Replace `<project-id>` with `ai-support-agent-f1902`:

   - **Chat Processor**:
     \`\`\`bash
     curl -X POST http://localhost:5001/<project-id>/us-central1/chat_processor \
     -H \"Content-Type: application/json\" \
     -d '{\"email\": \"daveyhmariam@gmail.com\", \"message\": \"I'\''m getting 503 errors on my Firebase app\"}'
     \`\`\`
   - **Get Chat History**:
     \`\`\`bash
     curl -X POST http://localhost:5001/<project-id>/us-central1/get_chat_history \
     -H \"Content-Type: application/json\" \
     -d '{\"email\": \"daveyhmariam@gmail.com\"}'
     \`\`\`
   - **Email Processor**:
     \`\`\`bash
     curl -X POST http://localhost:5001/<project-id>/us-central1/email_processor \
     -H \"Content-Type: application/json\" \
     -d '{\"subject\": \"Login Issue\", \"html\": \"Can'\''t log in!\", \"from\": {\"email\": \"daveyhmariam@gmail.com\"}}'
     \`\`\`

7. **Deploy to Firebase**:
   \`\`\`bash
   firebase login
   firebase functions:config:set gemini.key=<your-gemini-key> sheets.id=<your-sheet-id> gmail.auth_email=<your-gmail-email> gmail.app_password=<your-gmail-app-password> storage.bucket=ai-support-agent-f1902.appspot.com service_account.file=config/credentials.json
   firebase deploy --only functions,hosting
   \`\`\`
   - Chat UI: `https://<project-id>.web.app/chat.html`
   - Functions: `https://us-central1-<project-id>.cloudfunctions.net/<function-name>`

## Features

- **Chat UI**: `public/chat.html` for real-time tech support queries, with history retrieval.
- **Email Processing**: `email_processor` classifies emails, logs tickets to Google Sheets, sends Gmail responses.
- **Chat Processing**: `chat_processor` filters non-tech-support queries, saves tech support chats to Firebase Storage, logs tickets to Sheets, sends Gmail responses.
- **Chat History**: `get_chat_history` retrieves chat history from Storage.
- **Follow-up**: `follow_up_agent` runs daily (9 AM) via Cloud Scheduler, sends follow-up emails for open tickets.
- **Ticket System**: Google Sheets (`prepare me the spread sheet`) logs tickets for both chat and email queries.

## Testing

- **Chat**: Open `http://localhost:5000/chat.html`, use `daveyhmariam@gmail.com`:
  - Tech support query (e.g., \"I’m getting 503 errors\"): Saves to Storage, logs ticket in Sheets, sends email.
  - Non-tech-support query (e.g., \"When is the end of the world?\"): Rejects without saving.
  - Click \"Load History\" to view chats.
- **Email**: Use cURL to test `email_processor`, check Sheets and email.
- **Storage**: Verify `chat_history/<email>.json` in `http://localhost:4000/storage`.
- **Sheets**: Check `prepare me the spread sheet` for ticket rows.
- **Logs**: View in Emulator UI (`http://localhost:4000/functions`) or `firebase-debug.log`.

## Notes

- Uses Gmail SMTP instead of MailerSend for free-tier email delivery.
- Adheres to Firebase Spark Plan (free tier) with no billing.
- Ensure `config/credentials.json` has Google Sheets API permissions.
