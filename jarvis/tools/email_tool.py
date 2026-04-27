"""
===========================================================
J.A.R.V.I.S. — Email Tool (Gmail API)
===========================================================
OAuth2 authentication with Gmail API (free).
Read, send, reply, and manage emails.
===========================================================
"""

import os
import base64
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jarvis.config import GMAIL_CREDENTIALS_FILE, GMAIL_TOKEN_FILE

logger = logging.getLogger("jarvis.tools.email")


class EmailTool:
    """Gmail integration via Google API (free tier, OAuth2)."""

    def __init__(self, memory=None):
        self.memory = memory
        self._service = None
        self._available = False
        if GMAIL_CREDENTIALS_FILE and os.path.exists(GMAIL_CREDENTIALS_FILE):
            self._init_service()
        else:
            logger.info("Gmail not configured — email tool disabled")

    def _init_service(self):
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
            creds = None
            if os.path.exists(str(GMAIL_TOKEN_FILE)):
                creds = Credentials.from_authorized_user_file(str(GMAIL_TOKEN_FILE), SCOPES)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(GMAIL_CREDENTIALS_FILE, SCOPES)
                    creds = flow.run_local_server(port=0)
                with open(str(GMAIL_TOKEN_FILE), "w") as token:
                    token.write(creds.to_json())
            self._service = build("gmail", "v1", credentials=creds)
            self._available = True
            logger.info("Gmail API initialized")
        except Exception as e:
            logger.warning(f"Gmail init failed: {e}")

    def execute(self, params: dict) -> str:
        if not self._available:
            return "Email not configured, Sir. Set up Gmail credentials in .env."
        action = params.get("action", "read").lower()
        handlers = {"read": self._read, "send": self._send, "reply": self._reply, "search": self._search}
        handler = handlers.get(action)
        return handler(params) if handler else f"Unknown email action: '{action}'"

    def _read(self, params):
        count = params.get("count", 5)
        try:
            results = self._service.users().messages().list(userId="me", labelIds=["INBOX","UNREAD"], maxResults=count).execute()
            msgs = results.get("messages", [])
            if not msgs: return "No unread emails, Sir."
            lines = [f"You have {len(msgs)} unread email(s):\n"]
            for m in msgs:
                msg = self._service.users().messages().get(userId="me", id=m["id"], format="metadata", metadataHeaders=["From","Subject","Date"]).execute()
                h = {x["name"]: x["value"] for x in msg.get("payload",{}).get("headers",[])}
                lines.append(f"  • From: {h.get('From','Unknown')}\n    Subject: {h.get('Subject','(none)')}\n")
            return "\n".join(lines)
        except Exception as e:
            return f"Failed to read emails, Sir: {e}"

    def _send(self, params):
        to, subject, body = params.get("to",""), params.get("subject",""), params.get("body","")
        if not to: return "Specify recipient, Sir."
        if not body: return "Specify email body, Sir."
        try:
            msg = MIMEMultipart(); msg["to"]=to; msg["subject"]=subject or "(No Subject)"
            msg.attach(MIMEText(body,"plain"))
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            self._service.users().messages().send(userId="me", body={"raw": raw}).execute()
            return f"Email sent to {to}, Sir."
        except Exception as e:
            return f"Failed to send email, Sir: {e}"

    def _reply(self, params):
        body = params.get("body","")
        if not body: return "Specify reply message, Sir."
        try:
            results = self._service.users().messages().list(userId="me", labelIds=["INBOX","UNREAD"], maxResults=1).execute()
            msgs = results.get("messages",[])
            if not msgs: return "No email to reply to, Sir."
            orig = self._service.users().messages().get(userId="me", id=msgs[0]["id"], format="metadata", metadataHeaders=["From","Subject","Message-ID"]).execute()
            h = {x["name"]: x["value"] for x in orig.get("payload",{}).get("headers",[])}
            msg = MIMEMultipart(); msg["to"]=h.get("From",""); msg["subject"]=f"Re: {h.get('Subject','')}"
            msg["In-Reply-To"]=h.get("Message-ID",""); msg.attach(MIMEText(body,"plain"))
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            self._service.users().messages().send(userId="me", body={"raw":raw,"threadId":orig.get("threadId")}).execute()
            return f"Reply sent, Sir."
        except Exception as e:
            return f"Reply failed, Sir: {e}"

    def _search(self, params):
        query = params.get("query","")
        if not query: return "Specify search query, Sir."
        try:
            results = self._service.users().messages().list(userId="me", q=query, maxResults=5).execute()
            msgs = results.get("messages",[])
            if not msgs: return f"No emails matching '{query}', Sir."
            lines = [f"Found {len(msgs)} result(s):\n"]
            for m in msgs:
                msg = self._service.users().messages().get(userId="me", id=m["id"], format="metadata", metadataHeaders=["From","Subject"]).execute()
                h = {x["name"]: x["value"] for x in msg.get("payload",{}).get("headers",[])}
                lines.append(f"  • {h.get('Subject','(none)')} — {h.get('From','Unknown')}")
            return "\n".join(lines)
        except Exception as e:
            return f"Search failed, Sir: {e}"
