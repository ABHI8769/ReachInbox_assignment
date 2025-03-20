from slack_sdk import WebClient
import requests
from django.conf import settings
from ..models import Email

class NotificationService:
    def __init__(self):
        self.slack_client = WebClient(token=settings.SLACK_BOT_TOKEN if hasattr(settings, 'SLACK_BOT_TOKEN') else None)
        self.webhook_url = settings.WEBHOOK_URL if hasattr(settings, 'WEBHOOK_URL') else None

    def send_notification(self, email):
        """Send notifications for an email."""
        try:
            if email.category == 'interested':
                # Send Slack notification
                if self.slack_client and not email.slack_notification_sent:
                    message = (
                        f"*New Interested Email*\n"
                        f"From: {email.sender}\n"
                        f"Subject: {email.subject}\n"
                        f"Received: {email.received_date.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        f"```{email.body[:300]}...```"  # First 300 characters of body
                    )

                    response = self.slack_client.chat_postMessage(
                        channel="#email-notifications",  # Configure your channel
                        text=message,
                        mrkdwn=True
                    )

                    if response['ok']:
                        email.slack_notification_sent = True
                        email.save()

                # Trigger webhook
                if self.webhook_url and not email.webhook_triggered:
                    payload = {
                        'event': 'new_interested_email',
                        'email': {
                            'message_id': email.message_id,
                            'subject': email.subject,
                            'sender': email.sender,
                            'recipient': email.recipient,
                            'received_date': email.received_date.isoformat(),
                            'category': email.category
                        }
                    }

                    response = requests.post(self.webhook_url, json=payload)
                    if response.status_code == 200:
                        email.webhook_triggered = True
                        email.save()

            return True

        except Exception as e:
            print(f"Error sending notifications: {e}")
            return False 