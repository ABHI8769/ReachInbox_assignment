from elasticsearch import Elasticsearch
from django.conf import settings
from ..models import Email

class ElasticsearchService:
    def __init__(self):
        self.es = None
        if hasattr(settings, 'ELASTICSEARCH_HOST'):
            try:
                self.es = Elasticsearch([settings.ELASTICSEARCH_HOST])
            except Exception as e:
                print(f"Error connecting to Elasticsearch: {e}")
        self.index_name = 'emails'

    def setup_index(self):
        """Create and configure the email index."""
        try:
            # Check if index exists
            if not self.es.indices.exists(index=self.index_name):
                # Define index mapping
                mapping = {
                    'mappings': {
                        'properties': {
                            'message_id': {'type': 'keyword'},
                            'subject': {
                                'type': 'text',
                                'analyzer': 'standard',
                                'fields': {
                                    'keyword': {'type': 'keyword'}
                                }
                            },
                            'sender': {'type': 'keyword'},
                            'recipient': {'type': 'keyword'},
                            'body': {'type': 'text', 'analyzer': 'standard'},
                            'folder': {'type': 'keyword'},
                            'category': {'type': 'keyword'},
                            'received_date': {'type': 'date'},
                            'account_id': {'type': 'keyword'}
                        }
                    },
                    'settings': {
                        'number_of_shards': 1,
                        'number_of_replicas': 0
                    }
                }
                
                # Create index with mapping
                self.es.indices.create(index=self.index_name, body=mapping)
                
            return True
        except Exception as e:
            print(f"Error setting up Elasticsearch index: {e}")
            return False

    def index_email(self, email):
        """Index a single email in Elasticsearch."""
        if not self.es:
            return False

        try:
            # Prepare document
            doc = {
                'message_id': email.message_id,
                'subject': email.subject,
                'sender': email.sender,
                'recipient': email.recipient,
                'body': email.body,
                'folder': email.folder,
                'category': email.category,
                'received_date': email.received_date.isoformat(),
                'account_id': str(email.account.id)
            }
            
            # Index document
            self.es.index(
                index=self.index_name,
                id=email.message_id,
                document=doc
            )
            
            # Mark email as indexed
            email.es_indexed = True
            email.save()
            
            return True
        except Exception as e:
            print(f"Error indexing email: {e}")
            return False

    def search_emails(self, query: str, folder: str = None, account_id: str = None):
        """Search for emails in Elasticsearch."""
        try:
            # Build search query
            search_body = {
                'query': {
                    'bool': {
                        'must': [
                            {
                                'multi_match': {
                                    'query': query,
                                    'fields': ['subject^2', 'body']
                                }
                            }
                        ],
                        'filter': []
                    }
                },
                'sort': [
                    {'received_date': {'order': 'desc'}}
                ]
            }
            
            # Add folder filter if specified
            if folder:
                search_body['query']['bool']['filter'].append({
                    'term': {'folder': folder}
                })
            
            # Add account filter if specified
            if account_id:
                search_body['query']['bool']['filter'].append({
                    'term': {'account_id': account_id}
                })
            
            # Execute search
            response = self.es.search(
                index=self.index_name,
                body=search_body
            )
            
            # Extract hits
            hits = response['hits']['hits']
            total = response['hits']['total']['value']
            
            # Format results
            results = []
            for hit in hits:
                source = hit['_source']
                results.append({
                    'message_id': source['message_id'],
                    'subject': source['subject'],
                    'sender': source['sender'],
                    'recipient': source['recipient'],
                    'body': source['body'],
                    'folder': source['folder'],
                    'category': source['category'],
                    'received_date': source['received_date'],
                    'score': hit['_score']
                })
            
            return {
                'total': total,
                'results': results
            }
            
        except Exception as e:
            print(f"Error searching emails: {e}")
            return {
                'total': 0,
                'results': []
            }

    def close(self):
        """Close the Elasticsearch connection."""
        if self.es:
            self.es.close() 