import logging
from .vector_db_service import VectorDBService
from .ai_service import AIService
from django.conf import settings
from emails.models import Email

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        self.vector_db = VectorDBService()
        self.ai_service = AIService()
        
    def index_email(self, email):
        """Index an email in the vector database."""
        try:
            # Combine subject and body for better context
            text = f"Subject: {email.subject}\n\nBody: {email.body}"
            
            # Store metadata about the email
            metadata = {
                "email_id": email.id,
                "sender": email.sender,
                "recipient": email.recipient,
                "subject": email.subject,
                "received_date": str(email.received_date),
                "category": email.category
            }
            
            # Add to vector database
            success = self.vector_db.add_document(text, metadata)
            if success:
                logger.info(f"Successfully indexed email ID {email.id}")
                return True
            else:
                logger.error(f"Failed to index email ID {email.id}")
                return False
        except Exception as e:
            logger.error(f"Error indexing email: {e}")
            return False
    
    def index_all_emails(self):
        """Index all emails in the database."""
        emails = Email.objects.all()
        count = 0
        for email in emails:
            if self.index_email(email):
                count += 1
        logger.info(f"Indexed {count} out of {len(emails)} emails")
        return count
    
    def generate_reply_suggestion(self, email_id):
        """Generate a reply suggestion for an email using RAG."""
        try:
            # Get the email
            email = Email.objects.get(id=email_id)
            
            # Prepare query text
            query_text = f"Subject: {email.subject}\n\nBody: {email.body}"
            
            # Search for similar emails
            similar_emails = self.vector_db.similarity_search(query_text, top_k=3)
            
            if not similar_emails:
                logger.info(f"No similar emails found for email ID {email_id}")
                # Fall back to regular AI completion without RAG
                return self.generate_simple_reply(email)
            
            # Prepare context from similar emails
            context = self._prepare_context(similar_emails)
            
            # Generate reply using context
            prompt = f"""
You are an AI assistant helping to draft email replies. Use the following context from similar emails to craft a response to the current email.

Current Email:
From: {email.sender}
Subject: {email.subject}
Body: {email.body}

Similar Email Context:
{context}

Based on the context and the current email, draft a professional and helpful reply that continues any existing conversation threads appropriately. The reply should be concise, address the specific points in the email, and match the tone of previous communications.

Reply:
"""
            
            completion = self.ai_service.get_completion(prompt)
            if completion:
                logger.info(f"Generated RAG-based reply suggestion for email ID {email_id}")
                return completion
            else:
                logger.error(f"Failed to generate RAG-based reply for email ID {email_id}")
                return self.generate_simple_reply(email)
        except Email.DoesNotExist:
            logger.error(f"Email with ID {email_id} does not exist")
            return None
        except Exception as e:
            logger.error(f"Error generating reply suggestion: {e}")
            return None
    
    def _prepare_context(self, similar_emails):
        """Prepare context from similar emails."""
        context = ""
        for i, email_data in enumerate(similar_emails):
            context += f"--- Similar Email {i+1} (Similarity: {email_data['similarity']:.2f}) ---\n"
            context += f"Subject: {email_data['metadata'].get('subject', 'N/A')}\n"
            context += f"Body: {email_data['text'].replace('Subject:', '').replace('Body:', '')}\n\n"
        return context
    
    def generate_simple_reply(self, email):
        """Generate a simple reply without RAG for fallback."""
        prompt = f"""
Draft a professional and helpful reply to the following email:

From: {email.sender}
Subject: {email.subject}
Body: {email.body}

Reply:
"""
        return self.ai_service.get_completion(prompt) 