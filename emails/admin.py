from django.contrib import admin
from django.utils.html import format_html
from .models import Email, EmailAccount
import logging

logger = logging.getLogger(__name__)

@admin.register(EmailAccount)
class EmailAccountAdmin(admin.ModelAdmin):
    list_display = ('email', 'imap_server', 'imap_port', 'use_ssl', 'is_active', 'last_sync')
    list_filter = ('is_active', 'use_ssl')
    search_fields = ('email', 'imap_server')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('email', 'password', 'imap_server', 'imap_port', 'use_ssl')
        }),
        ('Status', {
            'fields': ('is_active', 'last_sync')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Email)
class EmailAdmin(admin.ModelAdmin):
    list_display = ('subject', 'sender', 'category', 'is_processed', 'has_reply_suggestion', 'created_at')
    list_filter = ('category', 'is_processed')
    search_fields = ('subject', 'sender', 'body')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['generate_reply_suggestions']
    
    def has_reply_suggestion(self, obj):
        return bool(obj.reply_suggestion)
    has_reply_suggestion.boolean = True
    has_reply_suggestion.short_description = 'Has Reply'
    
    def generate_reply_suggestions(self, request, queryset):
        count = 0
        for email in queryset:
            if email.generate_reply_suggestion():
                count += 1
        self.message_user(request, f"Generated reply suggestions for {count} out of {queryset.count()} emails.")
    generate_reply_suggestions.short_description = "Generate reply suggestions for selected emails"
    
    fieldsets = (
        (None, {
            'fields': ('subject', 'sender', 'body', 'category')
        }),
        ('Reply', {
            'fields': ('reply_suggestion',),
            'description': 'AI-generated reply suggestion for this email.'
        }),
        ('Status', {
            'fields': ('is_processed',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

# Add debug logging
logger.info("Registering Email and EmailAccount models in admin") 