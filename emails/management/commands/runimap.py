from django.core.management.base import BaseCommand
from emails.models import EmailAccount, Email
from emails.services.imap_service import IMAPService
from emails.services.ai_service import AIService
from emails.services.notification_service import NotificationService
from emails.services.elasticsearch_service import ElasticsearchService
import asyncio
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fetches emails from configured IMAP accounts and processes them'

    def handle(self, *args, **options):
        self.stdout.write('Starting IMAP service...')
        
        # Get active email accounts
        accounts = EmailAccount.objects.filter(is_active=True)
        
        if not accounts.exists():
            self.stdout.write(self.style.WARNING('No active email accounts found. Please add an email account in the admin interface.'))
            return

        # Initialize services
        ai_service = AIService()
        notification_service = NotificationService()
        elasticsearch_service = ElasticsearchService()

        for account in accounts:
            try:
                self.stdout.write(f'Processing account: {account.email}')
                
                # Create IMAP service instance
                imap_service = IMAPService(account)
                
                # Fetch emails
                emails = imap_service.fetch_emails()
                
                for email_data in emails:
                    try:
                        # Process email with AI service
                        category, reply = ai_service.process_email(email_data)
                        
                        # Create or update email in database
                        email, created = Email.objects.update_or_create(
                            message_id=email_data['message_id'],
                            defaults={
                                'subject': email_data['subject'],
                                'sender': email_data['sender'],
                                'recipient': email_data['recipient'],
                                'body': email_data['body'],
                                'folder': email_data['folder'],
                                'category': category,
                                'received_date': email_data['received_date'],
                                'account': account
                            }
                        )
                        
                        # Index email in Elasticsearch
                        if elasticsearch_service:
                            elasticsearch_service.index_email(email)
                        
                        # Send notification if needed
                        if notification_service and category in ['interested', 'meeting_booked']:
                            notification_service.send_notification(email)
                        
                        self.stdout.write(self.style.SUCCESS(f'Processed email: {email.subject}'))
                        
                    except Exception as e:
                        logger.error(f'Error processing email: {str(e)}')
                        continue
                
                # Update last sync time
                account.update_last_sync()
                
            except Exception as e:
                logger.error(f'Error processing account {account.email}: {str(e)}')
                continue
        
        self.stdout.write(self.style.SUCCESS('IMAP processing completed')) 