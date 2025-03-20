from django.test import TestCase
from django.utils import timezone
from .models import EmailAccount, Email
from .services.vector_db_service import VectorDBService
from .services.rag_service import RAGService
from unittest import skip
import os
from datetime import timedelta

class RAGServiceTests(TestCase):
    """Tests for the RAG (Retrieval Augmented Generation) service."""
    
    def setUp(self):
        """Set up test data."""
        # Create a test account
        self.account = EmailAccount.objects.create(
            email='test@example.com',
            password='password123',
            imap_server='imap.example.com',
            imap_port=993,
            use_ssl=True,
            is_active=True
        )
        
        # Create some test emails with different content
        self.emails = []
        topics = [
            ("Project Deadline", "The project deadline has been extended to next Friday."),
            ("Meeting Notes", "Here are the notes from our weekly meeting."),
            ("Product Launch", "We're launching our new product next month."),
            ("Feedback Request", "Could you provide feedback on the latest design?"),
            ("Budget Approval", "The budget for Q3 has been approved."),
        ]
        
        for i, (subject, body) in enumerate(topics):
            email = Email.objects.create(
                account=self.account,
                message_id=f'test-{i}@example.com',
                subject=subject,
                sender=f'sender-{i}@example.com',
                recipient='recipient@example.com',
                body=body,
                received_date=timezone.now() - timedelta(days=i),
                folder='INBOX',
                category='uncategorized'
            )
            self.emails.append(email)
    
    @skip("Skip if vector DB is not available")
    def test_vector_db_service_initialization(self):
        """Test that the vector DB service can be initialized."""
        try:
            vector_db = VectorDBService()
            self.assertIsNotNone(vector_db)
            self.assertTrue(hasattr(vector_db, 'collection'))
        except Exception as e:
            self.fail(f"VectorDBService initialization failed: {e}")
    
    @skip("Skip if vector DB is not available")
    def test_email_indexing(self):
        """Test that emails can be indexed in the vector DB."""
        try:
            rag_service = RAGService()
            count = rag_service.index_all_emails()
            self.assertEqual(count, len(self.emails))
        except Exception as e:
            self.fail(f"Email indexing failed: {e}")
    
    @skip("Skip if vector DB is not available")
    def test_similarity_search(self):
        """Test that similar emails can be found."""
        try:
            # First index the emails
            rag_service = RAGService()
            rag_service.index_all_emails()
            
            # Then search for similar emails
            vector_db = VectorDBService()
            query = "When is the project deadline?"
            results = vector_db.similarity_search(query, top_k=2)
            
            # We should get at least one result
            self.assertTrue(len(results) > 0)
            
            # The first result should be the email about project deadline
            self.assertIn("deadline", results[0]['metadata']['content'].lower())
        except Exception as e:
            self.fail(f"Similarity search failed: {e}")
    
    @skip("Skip if OpenAI API is not available")
    def test_reply_generation(self):
        """Test that replies can be generated."""
        # Get the first email
        email = self.emails[0]
        
        # Generate a reply
        success = email.generate_reply_suggestion()
        
        if os.environ.get('OPENAI_API_KEY'):
            self.assertTrue(success)
            self.assertIsNotNone(email.reply_suggestion)
            self.assertTrue(len(email.reply_suggestion) > 0)
        else:
            # If no API key, we should get a default response
            self.assertTrue(success)
            self.assertIn("Thank you for your email", email.reply_suggestion) 