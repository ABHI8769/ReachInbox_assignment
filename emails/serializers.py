from rest_framework import serializers
from .models import EmailAccount, Email

class EmailAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailAccount
        fields = ['id', 'email', 'password', 'imap_server', 'imap_port', 'use_ssl', 'last_sync', 'is_active']
        extra_kwargs = {
            'password': {'write_only': True}
        }

class EmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Email
        fields = [
            'id', 'message_id', 'subject', 'sender', 'recipient',
            'body', 'folder', 'received_date', 'category',
            'reply_suggestion', 'is_processed', 'created_at', 'updated_at'
        ]

class EmailSearchSerializer(serializers.Serializer):
    query = serializers.CharField(required=True)
    folder = serializers.CharField(required=False, allow_null=True)
    account_id = serializers.CharField(required=False, allow_null=True)

class EmailCategorySerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=Email.Category.choices)

class EmailReplySerializer(serializers.Serializer):
    reply = serializers.CharField() 