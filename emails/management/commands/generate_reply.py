from django.core.management.base import BaseCommand, CommandError
import logging
from emails.models import Email
from emails.services.rag_service import RAGService

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generate a RAG-based reply suggestion for a specific email'

    def add_arguments(self, parser):
        parser.add_argument('email_id', type=int, help='ID of the email to generate a reply for')

    def handle(self, *args, **options):
        email_id = options['email_id']
        
        try:
            email = Email.objects.get(id=email_id)
        except Email.DoesNotExist:
            raise CommandError(f'Email with ID {email_id} does not exist')
        
        self.stdout.write(f'Generating reply suggestion for email: {email.subject}')
        
        # Check if we already have a reply suggestion
        if email.reply_suggestion:
            self.stdout.write(self.style.WARNING('Email already has a reply suggestion:'))
            self.stdout.write(self.style.SUCCESS(email.reply_suggestion))
            return
        
        # Generate a new reply suggestion
        success = email.generate_reply_suggestion()
        
        if success and email.reply_suggestion:
            self.stdout.write(self.style.SUCCESS('Generated reply suggestion:'))
            self.stdout.write(self.style.SUCCESS(email.reply_suggestion))
        else:
            self.stdout.write(self.style.ERROR('Failed to generate reply suggestion'))