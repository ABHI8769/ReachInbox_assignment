import imaplib
import email
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta
import asyncio
from django.utils import timezone
from ..models import EmailAccount, Email

class IMAPService:
    def __init__(self, account: EmailAccount):
        self.account = account
        self.imap = None
        self.idle_task = None

    def connect(self):
        """Connect to the IMAP server."""
        try:
            self.imap = imaplib.IMAP4_SSL(self.account.imap_server, self.account.imap_port)
            self.imap.login(self.account.email, self.account.password)
            return True
        except Exception as e:
            print(f"Error connecting to IMAP server: {e}")
            return False

    def disconnect(self):
        """Disconnect from the IMAP server."""
        if self.imap:
            try:
                self.imap.logout()
            except:
                pass
            self.imap = None

    def fetch_emails(self):
        """Fetch emails from the last 30 days."""
        if not self.imap:
            if not self.connect():
                return []

        emails_list = []
        try:
            # Calculate date 30 days ago
            date_30_days_ago = (timezone.now() - timedelta(days=2)).strftime("%d-%b-%Y")
            
            # Select INBOX folder
            self.imap.select('INBOX')
            
            # Search for emails from the last 30 days
            _, message_numbers = self.imap.search(None, f'(SINCE {date_30_days_ago})')
            
            for num in message_numbers[0].split():
                # Fetch email message
                _, msg_data = self.imap.fetch(num, '(RFC822)')
                email_body = msg_data[0][1]
                
                # Parse email message
                msg = email.message_from_bytes(email_body)
                
                # Extract email data
                subject = msg['subject'] or ''
                sender = msg['from'] or ''
                recipient = msg['to'] or ''
                message_id = msg['message-id'] or ''
                received_date = parsedate_to_datetime(msg['date']) if msg['date'] else timezone.now()
                
                # Get email body
                body = ''
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            try:
                                payload = part.get_payload(decode=True)
                                if payload:
                                    # Try to detect encoding
                                    charset = part.get_content_charset() or 'utf-8'
                                    try:
                                        body = payload.decode(charset)
                                    except UnicodeDecodeError:
                                        # Fallback to utf-8 with error handling
                                        body = payload.decode('utf-8', errors='replace')
                            except Exception as e:
                                print(f"Error decoding part: {e}")
                                continue
                            break
                else:
                    try:
                        payload = msg.get_payload(decode=True)
                        if payload:
                            # Try to detect encoding
                            charset = msg.get_content_charset() or 'utf-8'
                            try:
                                body = payload.decode(charset)
                            except UnicodeDecodeError:
                                # Fallback to utf-8 with error handling
                                body = payload.decode('utf-8', errors='replace')
                    except Exception as e:
                        print(f"Error decoding message: {e}")
                        body = ''
                
                emails_list.append({
                    'message_id': message_id,
                    'subject': subject,
                    'sender': sender,
                    'recipient': recipient,
                    'body': body,
                    'received_date': received_date,
                })
                
        except Exception as e:
            print(f"Error fetching emails: {e}")
            self.disconnect()
            return []
        
        return emails_list

    def save_email(self, email_data, category='uncategorized'):
        """Save email to database."""
        try:
            email, created = Email.objects.update_or_create(
                message_id=email_data['message_id'],
                defaults={
                    'account': self.account,
                    'subject': email_data['subject'],
                    'sender': email_data['sender'],
                    'recipient': email_data['recipient'],
                    'body': email_data['body'],
                    'folder': 'INBOX',
                    'received_date': email_data['received_date'],
                    'category': category,
                }
            )
            return email
        except Exception as e:
            print(f"Error saving email: {e}")
            return None

    async def fetch_recent_emails(self):
        """Fetch emails from the last 30 days."""
        if not self.imap:
            if not await self.connect():
                return

        try:
            # Calculate date 30 days ago
            date_30_days_ago = (timezone.now() - timedelta(days=30)).strftime("%d-%b-%Y")
            
            # Select INBOX folder
            await self.imap.select('INBOX')
            
            # Search for emails from the last 30 days
            _, message_numbers = await self.imap.search(None, f'(SINCE {date_30_days_ago})')
            
            for num in message_numbers[0].split():
                # Fetch email message
                _, msg_data = await self.imap.fetch(num, '(RFC822)')
                email_body = msg_data[0][1]
                
                # Parse email message
                msg = email.message_from_bytes(email_body)
                
                # Extract email data
                subject = msg['subject'] or ''
                sender = msg['from'] or ''
                recipient = msg['to'] or ''
                message_id = msg['message-id'] or ''
                received_date = parsedate_to_datetime(msg['date']) if msg['date'] else timezone.now()
                
                # Get email body
                body = ''
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            try:
                                payload = part.get_payload(decode=True)
                                if payload:
                                    # Try to detect encoding
                                    charset = part.get_content_charset() or 'utf-8'
                                    try:
                                        body = payload.decode(charset)
                                    except UnicodeDecodeError:
                                        # Fallback to utf-8 with error handling
                                        body = payload.decode('utf-8', errors='replace')
                            except Exception as e:
                                print(f"Error decoding part: {e}")
                                continue
                            break
                else:
                    try:
                        payload = msg.get_payload(decode=True)
                        if payload:
                            # Try to detect encoding
                            charset = msg.get_content_charset() or 'utf-8'
                            try:
                                body = payload.decode(charset)
                            except UnicodeDecodeError:
                                # Fallback to utf-8 with error handling
                                body = payload.decode('utf-8', errors='replace')
                    except Exception as e:
                        print(f"Error decoding message: {e}")
                        body = ''
                
                # Create or update email in database
                Email.objects.update_or_create(
                    message_id=message_id,
                    defaults={
                        'account': self.account,
                        'subject': subject,
                        'sender': sender,
                        'recipient': recipient,
                        'body': body,
                        'folder': 'INBOX',
                        'received_date': received_date,
                    }
                )
                
        except Exception as e:
            print(f"Error fetching emails: {e}")
            await self.disconnect()
            return False
        
        return True

    async def idle_handler(self, response):
        """Handle new email notifications."""
        if response[0].endswith(b'EXISTS'):
            # New email received, fetch it
            await self.fetch_recent_emails()

    async def start_idle(self):
        """Start IDLE mode for real-time updates."""
        if not self.imap:
            if not await self.connect():
                return

        try:
            await self.imap.select('INBOX')
            
            while True:
                # Start IDLE mode
                idle = await self.imap.idle_start()
                
                try:
                    # Wait for new email notifications
                    response = await self.imap.idle_check(timeout=300)  # 5 minutes timeout
                    
                    if response:
                        await self.idle_handler(response)
                    
                finally:
                    # End IDLE mode
                    await self.imap.idle_done()
                
                # Small delay before next IDLE
                await asyncio.sleep(1)
                
        except Exception as e:
            print(f"Error in IDLE mode: {e}")
            await self.disconnect()

    async def start(self):
        """Start the IMAP service."""
        # Initial fetch of recent emails
        await self.fetch_recent_emails()
        
        # Start IDLE mode for real-time updates
        self.idle_task = asyncio.create_task(self.start_idle())

    async def stop(self):
        """Stop the IMAP service."""
        if self.idle_task:
            self.idle_task.cancel()
            try:
                await self.idle_task
            except asyncio.CancelledError:
                pass
            self.idle_task = None
        
        await self.disconnect() 