# apps/accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User,
    StudentExecutive,
    ExecutiveMeeting,
    MeetingAttendance,
    ExecutiveTask,
    ExecutiveDiscussion,
    DiscussionComment,
    ActivityLog,
    LoginAttempt
)


from django import forms

class UserAdminForm(forms.ModelForm):
    class Meta:
        model = User
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        user_type = cleaned_data.get('user_type')
        title = cleaned_data.get('title')
        if user_type == 'staff' and not title:
            raise forms.ValidationError("Staff members must have a title.")
        return cleaned_data
        
# ===========================
# User Admin
# ===========================
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'username', 
        'get_full_name', 
        'title',          # added title
        'email', 
        'user_type', 
        'program_type', 
        'level', 
        'is_active'
    )
    list_filter = (
        'user_type', 
        'program_type', 
        'level', 
        'is_active'
    )
    search_fields = (
        'username', 
        'email', 
        'first_name', 
        'last_name', 
        'title',         # allow search by title
        'student_id', 
        'staff_id'
    )
    ordering = ('username',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'title', 'email', 'profile_image', 'phone_number', 'date_of_birth', 'address')}),  # added title here
        ('Academic Info', {'fields': ('user_type', 'program_type', 'year_of_admission', 'level', 'student_id', 'staff_id')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Flags', {'fields': ('requires_password_change', 'failed_login_attempts', 'account_locked_until')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'user_type', 'program_type', 'level', 'title'),  # added title
        }),
    )

# ===========================
# Student Executive Admin
# ===========================
@admin.register(StudentExecutive)
class StudentExecutiveAdmin(admin.ModelAdmin):
    list_display = ('user', 'position', 'executive_level', 'tenure_status', 'is_active_executive')
    list_filter = ('position', 'executive_level', 'tenure_status', 'can_manage_events')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'position')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-tenure_start_date', 'position')


# ===========================
# Executive Meeting Admin
# ===========================
@admin.register(ExecutiveMeeting)
class ExecutiveMeetingAdmin(admin.ModelAdmin):
    list_display = ('title', 'meeting_type', 'status', 'date', 'organized_by', 'is_virtual')
    list_filter = ('meeting_type', 'status', 'is_virtual')
    search_fields = ('title', 'organized_by__user__username', 'venue')
    filter_horizontal = ('participants',)
    readonly_fields = ('qr_code', 'meeting_code')


# ===========================
# Meeting Attendance Admin
# ===========================
@admin.register(MeetingAttendance)
class MeetingAttendanceAdmin(admin.ModelAdmin):
    list_display = ('meeting', 'executive', 'check_in_time', 'check_in_method', 'ip_address')
    list_filter = ('check_in_method',)
    search_fields = ('executive__user__username', 'meeting__title')


# ===========================
# Executive Task Admin
# ===========================
@admin.register(ExecutiveTask)
class ExecutiveTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'assigned_to', 'assigned_by', 'priority', 'status', 'due_date', 'completed_date')
    list_filter = ('priority', 'status')
    search_fields = ('title', 'assigned_to__user__username', 'assigned_by__user__username')
    readonly_fields = ('created_at', 'updated_at')


# ===========================
# Executive Discussion Admin
# ===========================
@admin.register(ExecutiveDiscussion)
class ExecutiveDiscussionAdmin(admin.ModelAdmin):
    list_display = ('title', 'meeting', 'created_by', 'is_announcement', 'is_pinned', 'created_at')
    list_filter = ('is_announcement', 'is_pinned')
    search_fields = ('title', 'created_by__user__username')


# ===========================
# Discussion Comment Admin
# ===========================
@admin.register(DiscussionComment)
class DiscussionCommentAdmin(admin.ModelAdmin):
    list_display = ('discussion', 'author', 'created_at')
    search_fields = ('discussion__title', 'author__user__username')


# ===========================
# Activity Log Admin
# ===========================
@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action_type', 'timestamp', 'ip_address')
    list_filter = ('action_type',)
    search_fields = ('user__username',)
    readonly_fields = ('timestamp',)


# ===========================
# Login Attempt Admin
# ===========================
@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ('username', 'ip_address', 'timestamp', 'successful')
    list_filter = ('successful',)
    search_fields = ('username', 'ip_address')
    readonly_fields = ('timestamp',)