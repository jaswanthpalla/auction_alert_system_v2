import pandas as pd
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
import glob
import os
import logging
import base64
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def send_email_alert(api_key, sender_email, recipient_emails, days_threshold=7):
    """Send an email alert with upcoming auction deadlines as a CSV attachment."""
    try:
        # Validate inputs
        if not api_key or not sender_email or not recipient_emails:
            logger.error("Missing required environment variables: SENDGRID_API_KEY, SENDER_EMAIL, or RECIPIENT_EMAILS")
            return False

        # Ensure recipient_emails is a list
        if isinstance(recipient_emails, str):
            recipient_emails = [email.strip() for email in recipient_emails.split(',')]

        # Validate email addresses (basic check)
        if not all('@' in email for email in recipient_emails):
            logger.error("Invalid email address in recipient list: %s", recipient_emails)
            return False

        # Find the latest combined CSV file
        csv_files = glob.glob("auction_exports/combined_auctions_*.csv")
        if not csv_files:
            logger.error("No combined auction data found for email.")
            return False

        latest_csv = max(csv_files, key=os.path.getctime)
        df = pd.read_csv(latest_csv)

        # Filter for auctions with 0 <= days_until_submission <= threshold
        if 'days_until_submission' in df.columns:
            # Convert days_until_submission to numeric, replacing non-numeric (e.g., "-") with NaN
            df['days_until_submission'] = pd.to_numeric(df['days_until_submission'], errors='coerce')
            upcoming_df = df[(df['days_until_submission'] >= 0) & (df['days_until_submission'] <= days_threshold)]
            upcoming_df = upcoming_df.sort_values(by='days_until_submission')
        else:
            logger.error("Column 'days_until_submission' not found in the data.")
            return False

        # Create email content
        subject = f"Auction Alerts - Upcoming Deadlines ({datetime.now().strftime('%Y-%m-%d')})"
        if upcoming_df.empty:
            body = "No auctions with submission deadlines between 0 and 7 days. No CSV file attached."
            attachment = None
        else:
            # Prepare email body with a summary including Source
            body = f"Found {len(upcoming_df)} auctions with submission deadlines between 0 and 7 days:\n\n"
            for _, row in upcoming_df.iterrows():
                body += (
                    f"Auction ID: {row['Auction ID']}\n"
                    f"Bank/Organisation: {row['Bank/Organisation Name']}\n"
                    f"Source: {row['Source']}\n"
                    f"Last Date of Submission: {row['last_date_of_submission']}\n"
                    f"Days Until Submission: {row['days_until_submission']}\n"
                    f"---\n"
                )
            body += "\nFull details are attached in the CSV file."

            # Save the filtered dataframe to a temporary CSV file
            temp_csv = "upcoming_auctions.csv"
            upcoming_df.to_csv(temp_csv, index=False)

            # Read and encode the CSV file for attachment
            with open(temp_csv, 'rb') as f:
                data = f.read()
                encoded_file = base64.b64encode(data).decode()

            # Create the attachment
            attachment = Attachment(
                FileContent(encoded_file),
                FileName('upcoming_auctions.csv'),
                FileType('text/csv'),
                Disposition('attachment')
            )

            # Clean up the temporary file
            os.remove(temp_csv)

        # Set up the email
        message = Mail(
            from_email=sender_email,
            to_emails=recipient_emails,
            subject=subject,
            plain_text_content=body
        )

        # Attach the file if there are upcoming auctions
        if attachment:
            message.attachment = attachment

        # Send the email via SendGrid
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        logger.info("Email sent successfully to %s. Status code: %s", recipient_emails, response.status_code)
        return True

    except Exception as e:
        logger.error("Failed to send email: %s", e)
        return False

if __name__ == "__main__":
    # Retrieve environment variables
    api_key = os.getenv("SENDGRID_API_KEY")
    sender_email = os.getenv("SENDER_EMAIL")
    recipient_emails = os.getenv("RECIPIENT_EMAILS")
    
    # Send the email alert
    send_email_alert(api_key, sender_email, recipient_emails)
