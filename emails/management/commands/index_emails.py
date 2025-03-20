from django.core.management.base import BaseCommand
import logging
from emails.services.rag_service import RAGService

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Index all emails in the vector database for RAG-based suggestions'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting email indexing process...'))
        
        try:
            rag_service = RAGService()
            indexed_count = rag_service.index_all_emails()
            
            self.stdout.write(self.style.SUCCESS(f'Successfully indexed {indexed_count} emails'))
        except Exception as e:
            logger.error(f"Error during email indexing: {e}")
            self.stdout.write(self.style.ERROR(f'Error during email indexing: {str(e)}')) 