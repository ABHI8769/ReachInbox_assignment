import openai
from django.conf import settings
from ..models import Email
import logging
import re
import random

# Set up logging
logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.client = None
        self.use_fallback = False
        try:
            # Log the API key presence (not the actual key)
            api_key = settings.OPENAI_API_KEY
            logger.info(f"API key present: {bool(api_key)}")
            if not api_key:
                logger.error("OpenAI API key is not configured")
                self.use_fallback = True
                return

            # Initialize OpenAI client
            try:
                openai.api_key = api_key
                openai.api_base = settings.OPENAI_BASE_URL
                self.client = openai
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {str(e)}")
                self.client = None
                self.use_fallback = True

        except Exception as e:
            logger.error(f"Error in AIService initialization: {str(e)}")
            self.client = None
            self.use_fallback = True

    def get_completion(self, prompt, max_tokens=500, temperature=0.7):
        """Get a completion from OpenAI."""
        if not self.client or self.use_fallback:
            if not self.client:
                logger.error("OpenAI client is not initialized")
            if self.use_fallback:
                logger.info("Using fallback completion")
            
            return self._fallback_completion(prompt)

        try:
            # Get completion from OpenAI
            completion = self.client.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )

            # Extract text from response
            response_text = completion.choices[0].message.content.strip()
            return response_text

        except Exception as e:
            logger.error(f"Error getting completion: {str(e)}")
            return self._fallback_completion(prompt)
            
    def _fallback_completion(self, prompt):
        """Generate a fallback completion when OpenAI is unavailable."""
        # Extract the type of content requested from the prompt
        if "reply" in prompt.lower():
            return """Thank you for your email. I appreciate your message and will get back to you shortly with a more detailed response.

Best regards,
[Your Name]"""
        else:
            return "I apologize, but I'm unable to generate a response at this time. Please try again later."

    def _fallback_categorize(self, text):
        """
        Simple rule-based fallback categorization when OpenAI API is unavailable
        """
        text = (text or "").lower()
        
        # Simple rule-based categorization
        if re.search(r'(out\s*of\s*office|ooo|vacation|holiday|leave|away|not\s+available)', text):
            return 'out_of_office'
        
        if re.search(r'(meeting|appointment|schedule|calendar|meet|discuss|call|zoom|teams|google\s*meet)', text):
            return 'meeting_booked'
        
        if re.search(r'(unsubscribe|promotion|offer|deal|discount|sale|marketing|subscribe|newsletter)', text):
            return 'spam'
        
        if re.search(r'(not\s+interested|no\s+thank|decline|sorry|won\'t|cannot|won\'t\s+be|no\s+interest)', text):
            return 'not_interested'
        
        if re.search(r'(interest|inquiry|question|learn\s+more|tell\s+me|information|service|product)', text):
            return 'interested'
        
        # Default fallback
        return 'uncategorized'

    def _handle_api_error(self, exception, email_data=None, email=None):
        """
        Handle OpenAI API errors and decide if we should switch to fallback mode
        """
        error_msg = str(exception)
        logger.error(f"OpenAI API error: {error_msg}")
        
        # Check for quota error
        if "exceeded your current quota" in error_msg or "insufficient_quota" in error_msg:
            logger.warning("OpenAI API quota exceeded, switching to fallback mode")
            self.use_fallback = True
            
            # Get text to categorize
            if email_data:
                text = f"{email_data.get('subject', '')} {email_data.get('body', '')}"
            elif email:
                text = f"{email.subject} {email.body}"
            else:
                return 'uncategorized'
                
            return self._fallback_categorize(text)
        
        return 'uncategorized'

    def process_email(self, email_data):
        """Process an email using OpenAI."""
        if not self.client or self.use_fallback:
            if not self.client:
                logger.error("OpenAI client is not initialized")
            if self.use_fallback:
                logger.info("Using fallback categorization")
            
            # Use fallback categorization
            text = f"{email_data.get('subject', '')} {email_data.get('body', '')}"
            category = self._fallback_categorize(text)
            return category, None

        try:
            # Log the email being processed
            logger.info(f"Processing email: {email_data['subject']}")

            # Prepare prompt for categorization
            categorize_prompt = f"""
            Please categorize the following email into one of these categories:
            - interested: The sender shows interest in our product/service
            - meeting_booked: The sender confirms or requests a meeting
            - not_interested: The sender explicitly states they are not interested
            - spam: The email is spam or promotional
            - out_of_office: An out-of-office auto-reply
            - uncategorized: None of the above categories fit

            Subject: {email_data['subject']}
            From: {email_data['sender']}
            Body:
            {email_data['body']}

            Return ONLY the category name, nothing else.
            """

            # Get completion from OpenAI for categorization
            try:
                completion = self.client.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that categorizes emails."},
                        {"role": "user", "content": categorize_prompt}
                    ],
                    max_tokens=10,
                    temperature=0
                )
                logger.info("Successfully got completion from OpenAI")
            except Exception as e:
                return self._handle_api_error(e, email_data=email_data), None

            # Extract category from response
            category = completion.choices[0].message.content.strip().lower()
            logger.info(f"Categorized email as: {category}")

            return category, None

        except Exception as e:
            logger.error(f"Error processing email: {str(e)}")
            return self._handle_api_error(e, email_data=email_data), None

    def categorize_email(self, email: Email):
        """Categorize an email using OpenAI."""
        if not self.client or self.use_fallback:
            if not self.client:
                logger.error("OpenAI client is not initialized")
            if self.use_fallback:
                logger.info("Using fallback categorization")
            
            # Use fallback categorization
            text = f"{email.subject} {email.body}"
            return self._fallback_categorize(text)

        try:
            # Prepare prompt
            prompt = f"""
            Please categorize the following email into one of these categories:
            - interested: The sender shows interest in our product/service
            - meeting_booked: The sender confirms or requests a meeting
            - not_interested: The sender explicitly states they are not interested
            - spam: The email is spam or promotional
            - out_of_office: An out-of-office auto-reply
            - uncategorized: None of the above categories fit

            Subject: {email.subject}
            From: {email.sender}
            Body:
            {email.body}

            Return ONLY the category name, nothing else.
            """

            # Get completion from OpenAI
            completion = self.client.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that categorizes emails."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=10,
                temperature=0
            )

            # Extract category from response
            category = completion.choices[0].message.content.strip().lower()

            # Validate category
            valid_categories = [choice[0] for choice in Email.Category.choices]
            if category not in valid_categories:
                category = 'uncategorized'

            return category

        except Exception as e:
            return self._handle_api_error(e, email=email)

    def suggest_reply(self, email: Email):
        """Suggest a reply for an email."""
        if not self.client or self.use_fallback:
            if not self.client:
                logger.error("OpenAI client is not initialized")
            if self.use_fallback:
                logger.info("Using fallback reply suggestion")
            
            # Return a generic reply based on the email category
            category = email.category if email.category else self._fallback_categorize(f"{email.subject} {email.body}")
            
            generic_replies = {
                'interested': f"""
Dear {email.sender.split('@')[0]},

Thank you for your interest in our services. We appreciate you reaching out to us.

I'd be happy to provide more information and answer any questions you may have. Can we schedule a brief call this week to discuss your specific needs?

Best regards,
Your Name
Company Name
                """,
                'meeting_booked': f"""
Dear {email.sender.split('@')[0]},

Thank you for scheduling a meeting with us. I'm looking forward to our conversation.

I've added the appointment to my calendar. Please let me know if you need any specific information from me before our meeting.

Best regards,
Your Name
Company Name
                """,
                'not_interested': f"""
Dear {email.sender.split('@')[0]},

Thank you for your response. I understand that our services may not be what you're looking for at this time.

We appreciate your consideration and would be happy to assist you in the future should your needs change.

Best regards,
Your Name
Company Name
                """,
                'out_of_office': "",  # No need to reply to out-of-office messages
                'spam': "",  # No need to reply to spam
                'uncategorized': f"""
Dear {email.sender.split('@')[0]},

Thank you for your email. I've received your message and will get back to you with a more detailed response soon.

Best regards,
Your Name
Company Name
                """
            }
            
            return generic_replies.get(category, generic_replies['uncategorized'])

        try:
            # Prepare prompt
            prompt = f"""
            Please suggest a professional and friendly reply to the following email:

            Subject: {email.subject}
            From: {email.sender}
            Body:
            {email.body}

            The reply should be:
            1. Professional and courteous
            2. Address the main points in the email
            3. Include a clear next step or call to action
            4. End with a professional signature
            """

            # Get completion from OpenAI
            completion = self.client.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that drafts email replies."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )

            # Extract reply from response
            reply = completion.choices[0].message.content.strip()

            return reply

        except Exception as e:
            logger.error(f"Error suggesting reply: {str(e)}")
            # Fall back to generic reply
            return self._handle_api_error(e, email=email) 