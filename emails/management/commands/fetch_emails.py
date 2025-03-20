from django.core.management.base import BaseCommand
from emails.models import EmailAccount
from emails.services.imap_service import IMAPService
from emails.services.ai_service import TextAnalysisService
from emails.services.elasticsearch_service import ElasticsearchService
from emails.services.notification_service import NotificationService

class Command(BaseCommand):
    help = 'Fetches emails from configured email accounts'

    def handle(self, *args, **options):
        self.stdout.write('Starting email fetch process...')
        
        # Initialize services
        es_service = ElasticsearchService()
        text_analysis_service = TextAnalysisService()
        notif_service = NotificationService()
        
        # Get all email accounts
        email_accounts = EmailAccount.objects.all()
        
        if not email_accounts.exists():
            self.stdout.write(self.style.WARNING('No email accounts configured. Please add an email account first.'))
            return
            
        for account in email_accounts:
            self.stdout.write(f'Processing account: {account.email}')
            try:
                # Initialize IMAP service for this account
                imap_service = IMAPService(account)
                
                # Fetch emails
                emails = imap_service.fetch_emails()
                self.stdout.write(f'Fetched {len(emails)} emails from {account.email}')
                
                # Process each email
                for email_data in emails:
                    # Save email to database
                    email = imap_service.save_email(email_data)
                    if email:
                        # Categorize email
                        category = text_analysis_service.categorize_email(email)
                        email.category = category
                        email.save()
                        
                        # Index in Elasticsearch
                        es_service.index_email(email)
                        
                        # Send notification if needed
                        if category in ['interested', 'meeting_booked']:
                            notif_service.send_notification(email)
                        
                self.stdout.write(self.style.SUCCESS(f'Successfully processed emails for {account.email}'))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error processing account {account.email}: {str(e)}'))
                
        self.stdout.write(self.style.SUCCESS('Email fetch process completed')) 