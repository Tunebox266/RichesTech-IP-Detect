# apps/messaging/admin.py

from django.contrib import admin
from .models import *


# ===============================
# Message Attachment Inline
# ===============================

class MessageAttachmentInline(admin.TabularInline):
    model = MessageAttachment
    extra = 0


# ===============================
# Message Admin
# ===============================

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "sender",
        "recipient",
        "subject",
        "sent_at",
        "is_broadcast",
        "is_urgent",
        "is_replied"
    )

    list_filter = (
        "is_broadcast",
        "is_urgent",
        "sent_at"
    )

    search_fields = (
        "subject",
        "body",
        "sender__username",
        "recipient__username"
    )

    inlines = [MessageAttachmentInline]

    readonly_fields = ("sent_at", "read_at")


# ===============================
# Conversation Admin
# ===============================

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        "subject",
        "last_message_at",
        "created_at"
    )

    search_fields = ("subject",)


# ===============================
# Broadcast Admin
# ===============================

@admin.register(Broadcast)
class BroadcastAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "priority",
        "created_by",
        "scheduled_for",
        "sent_at",
        "is_active"
    )

    list_filter = ("priority", "is_active")
    search_fields = ("title", "content")

    filter_horizontal = ("recipients",)

    readonly_fields = ("sent_at", "view_count", "acknowledgment_count")


# ===============================
# Notification Admin
# ===============================

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "notification_type",
        "title",
        "is_read",
        "created_at"
    )

    list_filter = ("notification_type", "is_read")
    search_fields = ("title", "content")

    readonly_fields = ("created_at", "read_at")


# ===============================
# Complaint Admin
# ===============================

class ComplaintAttachmentInline(admin.TabularInline):
    model = ComplaintAttachment
    extra = 0


class ComplaintResponseInline(admin.TabularInline):
    model = ComplaintResponse
    extra = 0


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "complaint_type",
        "subject",
        "status",
        "is_anonymous",
        "created_at"
    )

    list_filter = (
        "status",
        "complaint_type",
        "is_anonymous"
    )

    search_fields = (
        "subject",
        "description",
        "user__username"
    )

    inlines = [
        ComplaintAttachmentInline,
        ComplaintResponseInline
    ]


# ===============================
# Complaint Response Admin
# ===============================

@admin.register(ComplaintResponse)
class ComplaintResponseAdmin(admin.ModelAdmin):
    list_display = (
        "complaint",
        "responder",
        "created_at"
    )

    search_fields = (
        "complaint__subject",
        "responder__username"
    )


# ===============================
# Complaint Attachment Admin
# ===============================

@admin.register(ComplaintAttachment)
class ComplaintAttachmentAdmin(admin.ModelAdmin):
    list_display = (
        "filename",
        "complaint",
        "uploaded_at"
    )

    search_fields = ("filename",)


# ===============================
# Notification Preference Admin
# ===============================

@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "email_digest", "updated_at")

    search_fields = ("user__username",)