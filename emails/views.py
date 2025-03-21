from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404, render
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import EmailAccount, Email
from .serializers import (
    EmailAccountSerializer, EmailSerializer,
    EmailSearchSerializer, EmailCategorySerializer,
    EmailReplySerializer
)
from .services.imap_service import IMAPService
from .services.elasticsearch_service import ElasticsearchService
from .services.ai_service import AIService
from .services.notification_service import NotificationService
from .services.rag_service import RAGService
from .services.vector_db_service import VectorDBService
from rest_framework.pagination import PageNumberPagination
import asyncio
import logging

logger = logging.getLogger(__name__)

class EmailListView(TemplateView):
    template_name = 'emails/email_list.html'

class AccountListView(TemplateView):
    template_name = 'emails/account_list.html'

@method_decorator(csrf_exempt, name='dispatch')
class EmailAccountViewSet(viewsets.ModelViewSet):
    queryset = EmailAccount.objects.all()
    serializer_class = EmailAccountSerializer

    @action(detail=True, methods=['post'])
    async def sync(self, request, pk=None):
        """Manually trigger email synchronization for an account."""
        account = self.get_object()
        
        # Initialize services
        imap_service = IMAPService(account)
        
        try:
            # Start sync
            await imap_service.fetch_recent_emails()
            return Response({'status': 'sync started'})
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            await imap_service.stop()

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class EmailViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Email.objects.all()
    serializer_class = EmailSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """Filter emails by folder and account."""
        queryset = super().get_queryset()
        
        folder = self.request.query_params.get('folder', None)
        account_id = self.request.query_params.get('account_id', None)
        
        if folder:
            queryset = queryset.filter(folder=folder)
        if account_id:
            queryset = queryset.filter(account_id=account_id)
            
        return queryset.order_by('-received_date')

    @action(detail=False, methods=['post'])
    async def search(self, request):
        """Search emails using Elasticsearch."""
        serializer = EmailSearchSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        es_service = ElasticsearchService()
        try:
            results = await es_service.search_emails(
                query=serializer.validated_data['query'],
                folder=serializer.validated_data.get('folder'),
                account_id=serializer.validated_data.get('account_id')
            )
            
            # Add pagination info to response
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 10))
            
            total_results = len(results.get('results', []))
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            
            paginated_results = {
                'count': total_results,
                'next': None if end_idx >= total_results else f"?page={page+1}&page_size={page_size}",
                'previous': None if page <= 1 else f"?page={page-1}&page_size={page_size}",
                'results': results.get('results', [])[start_idx:end_idx]
            }
            
            return Response(paginated_results)
        finally:
            await es_service.close()

    @action(detail=True, methods=['post'])
    async def categorize(self, request, pk=None):
        """Categorize an email using AI."""
        email = self.get_object()
        
        ai_service = AIService()
        notification_service = NotificationService()
        
        try:
            # Categorize email
            category = await ai_service.categorize_email(email)
            
            # Send notifications if needed
            await notification_service.notify(email)
            
            serializer = EmailCategorySerializer({'category': category})
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def suggest_reply(self, request, pk=None):
        """Generate a RAG-based reply suggestion for an email."""
        email = self.get_object()
        
        try:
            # First check if we already have a reply suggestion
            if email.reply_suggestion:
                serializer = EmailReplySerializer({'reply': email.reply_suggestion})
                return Response(serializer.data)
            
            # Otherwise, generate a new reply suggestion
            success = email.generate_reply_suggestion()
            
            if success and email.reply_suggestion:
                serializer = EmailReplySerializer({'reply': email.reply_suggestion})
                return Response(serializer.data)
            else:
                return Response(
                    {'error': 'Failed to generate reply suggestion'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            logger.error(f"Error suggesting reply: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    @action(detail=False, methods=['post'])
    def index_for_rag(self, request):
        """Index all emails for RAG-based suggestions."""
        try:
            rag_service = RAGService()
            count = rag_service.index_all_emails()
            return Response({'indexed_count': count})
        except Exception as e:
            logger.error(f"Error indexing emails for RAG: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def similar_emails(self, request, pk=None):
        """Find similar emails using the vector database."""
        email = self.get_object()
        
        try:
            # Prepare query text from the email
            query_text = f"Subject: {email.subject}\n\nBody: {email.body}"
            
            # Initialize vector DB service
            vector_db = VectorDBService()
            
            # Get the number of results to return
            top_k = int(request.query_params.get('top_k', 3))
            
            # Search for similar emails
            similar_emails = vector_db.similarity_search(query_text, top_k=top_k)
            
            if not similar_emails:
                return Response({'similar_emails': []})
            
            # Format the results
            results = []
            for item in similar_emails:
                # Get the email ID from metadata
                email_id = item['metadata'].get('email_id')
                
                # If we have an email ID, fetch the full email details
                if email_id:
                    try:
                        similar_email = Email.objects.get(id=email_id)
                        results.append({
                            'id': similar_email.id,
                            'subject': similar_email.subject,
                            'sender': similar_email.sender,
                            'similarity_score': item['similarity'],
                            'category': similar_email.category
                        })
                    except Email.DoesNotExist:
                        # If email doesn't exist, just use the metadata
                        results.append({
                            'id': email_id,
                            'subject': item['metadata'].get('subject', 'N/A'),
                            'sender': item['metadata'].get('sender', 'N/A'),
                            'similarity_score': item['similarity'],
                            'category': item['metadata'].get('category', 'N/A')
                        })
                else:
                    # If no email ID in metadata, return just the text and similarity
                    results.append({
                        'text': item['text'],
                        'similarity_score': item['similarity']
                    })
            
            return Response({'similar_emails': results})
        except Exception as e:
            logger.error(f"Error finding similar emails: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 