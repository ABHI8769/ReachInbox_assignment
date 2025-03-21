# ReachinBox: AI-Powered Email Management System

ReachinBox is a sophisticated email management system that provides real-time synchronization, AI-based categorization, and intelligent reply suggestions.

## Features

### 1. Real-Time Email Synchronization
- Sync multiple IMAP accounts simultaneously (minimum 2 accounts)
- Fetches at least 30 days of email history
- Uses persistent IMAP connections with IDLE mode for real-time updates
- No cron jobs needed - updates are instant!

### 2. Elasticsearch-Powered Search
- Emails stored in locally hosted Elasticsearch (Docker-based)
- Advanced indexing for powerful search capabilities
- Filter emails by folder and account
- Full-text search across all email content

### 3. AI-Based Email Categorization
- Intelligent model categorizes emails into:
  - Interested
  - Meeting Booked
  - Not Interested
  - Spam
  - Out of Office
- Automatic categorization upon email receipt
- Manual recategorization supported

### 4. Integrations
- Slack notifications for all "Interested" emails
- Webhook triggers (compatible with webhook.site) for external automation
- Seamless integration with existing workflows

### 5. User-Friendly Interface
- Clean, modern UI to browse and manage emails
- Filter by folder and account
- View AI categorization for each email
- Powerful search functionality powered by Elasticsearch

### 6. AI-Powered Reply Suggestions
- Uses Retrieval-Augmented Generation (RAG) with vector database
- Contextually relevant reply suggestions
- Includes product details and outreach information
- Example: For interested leads, automatically suggests replies with meeting booking links

## Setup & Usage

### Email Account Configuration
1. Access the admin site at `http://127.0.0.1:8000/admin/`
2. Navigate to the Accounts section
3. Add new email accounts with the following details:
   - Email address
   - Password
   - IMAP server settings
   - SMTP server settings

### Admin Site Functionalities
The admin site provides additional capabilities:
- Email account management
- Manual email categorization and review
- System configuration and monitoring
- Integration settings (Slack, webhooks)

### Accessing the Email Interface
The main email interface is available at:
```
http://127.0.0.1:8000/emails/app/emails/
```

Here you can:
- View all synchronized emails
- Filter by folder or account
- Search for specific content
- See AI categorizations
- Get reply suggestions
- Find similar emails

## Technical Requirements
- Docker for Elasticsearch container
- Python 3.8+
- Django framework
- Vector database for RAG implementation
- IMAP library with IDLE support
- Slack and webhook libraries

## Installation
1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Start Elasticsearch: `docker-compose up -d elasticsearch`
4. Run migrations: `python manage.py migrate`
5. Create a superuser: `python manage.py createsuperuser`
6. Start the server: `python manage.py runserver`
7. Configure email accounts via the admin interface
8. Access the email interface at `http://127.0.0.1:8000/emails/app/emails/` 