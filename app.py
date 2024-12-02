import os
import base64
import logging
from flask import Flask, request, redirect, url_for, render_template
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import google.auth
import google.auth.transport.requests

app = Flask(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
CLIENT_SECRET_FILE = "credentials.json"
APPLICATION_NAME = "Time Capsule"
REDIRECT_URI = "http://localhost:60658/oauth2callback"

logging.basicConfig(level=logging.INFO)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/oauth2callback")
def oauth2callback():
    flow = InstalledAppFlow.from_client_secrets_file(
        "credentials.json",
        scopes=["https://www.googleapis.com/auth/gmail.send"],
        redirect_uri="http://localhost:60664/",
    )
    creds = flow.fetch_token(authorization_response=request.url)
    with open("token.json", "w") as token:
        token.write(creds.to_json())
    return redirect(url_for("index"))


@app.route("/submit", methods=["POST"])
def submit():
    email = request.form["email"]
    links = request.form.get("links", "")
    scheduled_time = request.form["schedule_time"]
    image_data = request.form.get("image_data", "")
    logging.info(f"Form submitted by: {email}")
    logging.info(f"Links: {links}")
    logging.info(f"Scheduled Time: {scheduled_time}")
    try:
        send_email(email, links, scheduled_time, image_data)
        return redirect(url_for("index"))
    except Exception as e:
        logging.error(f"Error processing time capsule: {e}")
        return "An error occurred while processing your request."


def get_gmail_service():
    creds = None
    if os.path.exists("token.json"):
        creds, _ = google.auth.load_credentials_from_file("token.json")
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI
            )
            creds = flow.run_local_server(port=60658)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def send_email(to, links, scheduled_time, image_data):
    try:
        service = get_gmail_service()
        subject = "Your Time Capsule Submission"
        body = f"Links to save: {links}\nScheduled time: {scheduled_time}\n\nImage data: {image_data}"
        message = MIMEMultipart()
        message["to"] = to
        message["subject"] = subject
        msg = MIMEText(body)
        message.attach(msg)
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        send_message = (
            service.users()
            .messages()
            .send(userId="me", body={"raw": raw_message})
            .execute()
        )
        logging.info(f"Sent message to {to} Message Id: {send_message['id']}")
        if os.path.exists("token.json"):
            os.remove("token.json")
            logging.info("Deleted token.json")
    except Exception as error:
        logging.error(f"An error occurred while sending email: {error}")
        raise


if __name__ == "__main__":
    app.run(debug=True, port=60664)
