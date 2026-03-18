# apps/attendance/admin.py

from django.contrib import admin
from .models import AttendanceSession, AttendanceRecord


# ===============================
# Attendance Record Inline (Optional but Powerful)
# ===============================

class AttendanceRecordInline(admin.TabularInline):
    model = AttendanceRecord
    extra = 0
    readonly_fields = ("checked_in_at",)


# ===============================
# Attendance Session Admin
# ===============================

@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "session_type",
        "date",
        "venue",
        "is_active",
        "get_attendance_count"
    )

    list_filter = ("session_type", "is_active", "date")
    search_fields = ("title", "venue")

    readonly_fields = ("created_at",)

    inlines = [AttendanceRecordInline]


# ===============================
# Attendance Record Admin
# ===============================

@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = (
        "session",
        "student",
        "checked_in_at",
        "method",
        "checked_in_by"
    )

    list_filter = ("method", "checked_in_at")
    search_fields = (
        "student__username",
        "student__first_name",
        "student__last_name"
    )

    readonly_fields = ("checked_in_at",)