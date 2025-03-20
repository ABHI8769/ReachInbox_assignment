from django.core.management.base import BaseCommand
from emails.models import EmailAccount

class Command(BaseCommand):
    help = 'Creates a test email account for development'

    def handle(self, *args, **options):
        # Create a test account with Gmail settings
        account = EmailAccount.objects.create(
            email='abhijeet.goswami78@gmail.com',  # Replace with your Gmail address
            password='cyiq adln fdpt mvzx',  # Replace with your Gmail app password
            imap_server='imap.gmail.com',
            imap_port=993,
            use_ssl=True,
            is_active=True
        )
        self.stdout.write(self.style.SUCCESS(f'Successfully created test account {account.email}')) 