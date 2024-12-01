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

# Flask Setup
app = Flask(__name__)

# Google API OAuth 2.0 configuration
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
CLIENT_SECRET_FILE = "credentials.json"  # Path to your credentials file
APPLICATION_NAME = "Time Capsule"

# Log setup
logging.basicConfig(level=logging.INFO)

# Set the fixed redirect URI (Make sure this is consistent with the one in the Google Cloud Console)
REDIRECT_URI = "http://localhost:60658/oauth2callback"  # Changed port here


# Route for the form (Main Page)
@app.route("/")
def index():
    return render_template("index.html")  # Your HTML form for capsule submission


# Route for OAuth callback (this will handle the redirect)
@app.route("/oauth2callback")
def oauth2callback():
    flow = InstalledAppFlow.from_client_secrets_file(
        "credentials.json",
        scopes=["https://www.googleapis.com/auth/gmail.send"],
        redirect_uri="http://localhost:60664/",  # Update with the new port
    )

    creds = flow.fetch_token(authorization_response=request.url)

    # Save the credentials for later use
    with open("token.json", "w") as token:
        token.write(creds.to_json())

    return redirect(
        url_for("index")
    )  # Redirect back to the form after successful authentication


# Route for form submission
@app.route("/submit", methods=["POST"])
def submit():
    email = request.form["email"]
    links = request.form.get("links", "")
    scheduled_time = request.form["schedule_time"]
    image_data = request.form.get("image_data", "")

    # Logging for debugging
    logging.info(f"Form submitted by: {email}")
    logging.info(f"Links: {links}")
    logging.info(f"Scheduled Time: {scheduled_time}")

    try:
        # Call the function to send email via Gmail OAuth2
        send_email(email, links, scheduled_time, image_data)
        return redirect(url_for("index"))  # Redirect back to the form after submission
    except Exception as e:
        logging.error(f"Error processing time capsule: {e}")
        return "An error occurred while processing your request."


def get_gmail_service():
    """Authenticate with Gmail API using OAuth 2.0"""
    creds = None
    if os.path.exists("token.json"):
        creds, _ = google.auth.load_credentials_from_file("token.json")
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Ensure redirect_uri is static
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE,
                scopes=SCOPES,
                redirect_uri=REDIRECT_URI,  # Use static redirect URI here
            )
            creds = flow.run_local_server(port=60658)  # Fixed port for OAuth callback
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def send_email(to, links, scheduled_time, image_data):
    """Send an email using Gmail API with OAuth 2.0"""
    try:
        service = get_gmail_service()

        # Create the email content
        subject = "Your Time Capsule Submission"
        body = f"Links to save: {links}\nScheduled time: {scheduled_time}\n\nImage data: {image_data}"

        message = MIMEMultipart()
        message["to"] = to
        message["subject"] = subject
        msg = MIMEText(body)
        message.attach(msg)

        # Encode the email to base64
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        # Send the email
        send_message = (
            service.users()
            .messages()
            .send(userId="me", body={"raw": raw_message})
            .execute()
        )
        logging.info(f"Sent message to {to} Message Id: {send_message['id']}")
        # Delete token.json after sending the email
        if os.path.exists("token.json"):
            os.remove("token.json")
            logging.info("Deleted token.json")
    except Exception as error:
        logging.error(f"An error occurred while sending email: {error}")
        raise


if __name__ == "__main__":
    app.run(debug=True, port=60664)
