from django.db import models
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class EmailAccount(models.Model):
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)  # Store securely in production
    imap_server = models.CharField(max_length=255)
    imap_port = models.IntegerField(default=993)
    use_ssl = models.BooleanField(default=True)
    last_sync = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = 'Email Account'
        verbose_name_plural = 'Email Accounts'

class Email(models.Model):
    class Category(models.TextChoices):
        INTERESTED = 'interested', 'Interested'
        MEETING_BOOKED = 'meeting_booked', 'Meeting Booked'
        NOT_INTERESTED = 'not_interested', 'Not Interested'
        SPAM = 'spam', 'Spam'
        OUT_OF_OFFICE = 'out_of_office', 'Out of Office'
        UNCATEGORIZED = 'uncategorized', 'Uncategorized'

    account = models.ForeignKey(EmailAccount, on_delete=models.CASCADE, related_name='emails')
    message_id = models.CharField(max_length=255, unique=True)
    subject = models.CharField(max_length=1000)
    sender = models.CharField(max_length=255)
    recipient = models.CharField(max_length=255)
    body = models.TextField()
    folder = models.CharField(max_length=255)
    received_date = models.DateTimeField()
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.UNCATEGORIZED
    )
    reply_suggestion = models.TextField(blank=True, null=True)
    is_processed = models.BooleanField(default=False)
    slack_notification_sent = models.BooleanField(default=False)
    webhook_triggered = models.BooleanField(default=False)
    es_indexed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.subject} - {self.sender}"

    def generate_reply_suggestion(self):
        """Generate and save a reply suggestion using RAG"""
        from emails.services.rag_service import RAGService
        
        try:
            rag_service = RAGService()
            suggestion = rag_service.generate_reply_suggestion(self.id)
            if suggestion:
                self.reply_suggestion = suggestion
                self.save(update_fields=['reply_suggestion'])
                logger.info(f"Generated reply suggestion for email ID {self.id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error generating reply suggestion: {e}")
            return False

    class Meta:
        verbose_name = 'Email'
        verbose_name_plural = 'Emails'
        indexes = [
            models.Index(fields=['message_id']),
            models.Index(fields=['category']),
            models.Index(fields=['folder']),
            models.Index(fields=['received_date']),
        ]

# Add debug logging
logger.info("Email and EmailAccount models loaded") 