# apps/events/admin.py

from django.contrib import admin
from .models import (
    Event,
    EventAttendee,
    AttendanceSession,
    AttendanceRecord,
    AttendanceCode,
    EventFeedback,
    EventReminder
)

# ================================
# Inline Models
# ================================

class EventAttendeeInline(admin.TabularInline):
    model = EventAttendee
    extra = 0
    readonly_fields = ("registered_at", "checked_in_at")


class AttendanceSessionInline(admin.TabularInline):
    model = AttendanceSession
    extra = 0


class AttendanceRecordInline(admin.TabularInline):
    model = AttendanceRecord
    extra = 0
    readonly_fields = ("checked_in_at",)


class EventFeedbackInline(admin.TabularInline):
    model = EventFeedback
    extra = 0


# ================================
# Event Admin
# ================================

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "event_type",
        "start_date",
        "end_date",
        "venue",
        "is_active",
        "get_attendee_count",
        "get_checked_in_count"
    )

    list_filter = (
        "event_type",
        "is_active",
        "start_date"
    )

    search_fields = (
        "title",
        "description",
        "venue",
        "created_by__username"
    )

    inlines = [
        EventAttendeeInline,
        AttendanceSessionInline,
        EventFeedbackInline
    ]

    readonly_fields = ("created_at", "updated_at")


# ================================
# Attendance Session Admin
# ================================

@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "event",
        "session_type",
        "start_time",
        "end_time",
        "is_active",
        "get_checked_in_count"
    )

    list_filter = ("session_type", "is_active")
    search_fields = ("name", "event__title")

    readonly_fields = ("qr_code", "session_code", "created_at")


# ================================
# Attendance Record Admin
# ================================

@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "session",
        "checked_in_at",
        "check_in_method",
        "ip_address"
    )

    list_filter = ("check_in_method", "checked_in_at")
    search_fields = (
        "user__username",
        "session__name",
        "session__event__title"
    )


# ================================
# Attendance Code Admin
# ================================

@admin.register(AttendanceCode)
class AttendanceCodeAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "event",
        "session",
        "code_type",
        "valid_from",
        "valid_until",
        "current_uses",
        "is_active"
    )

    list_filter = ("code_type", "is_active")
    search_fields = ("code", "event__title")

    readonly_fields = ("created_at",)


# ================================
# Feedback Admin
# ================================

@admin.register(EventFeedback)
class EventFeedbackAdmin(admin.ModelAdmin):
    list_display = ("event", "user", "rating", "created_at")

    list_filter = ("rating",)
    search_fields = ("event__title", "user__username")


# ================================
# Reminder Admin
# ================================

@admin.register(EventReminder)
class EventReminderAdmin(admin.ModelAdmin):
    list_display = (
        "event",
        "reminder_type",
        "remind_at",
        "sent",
        "sent_at"
    )

    list_filter = ("reminder_type", "sent")
    search_fields = ("event__title",)