from django.contrib import admin
from django.utils.html import format_html
from .models import (
    AcademicSetting,
    Announcement,
    Notification,
    BlogPost,
    VideoVlog,
    StudentExecutive,
    StudentDocument,
    About,
    ExecutiveTeam,
    ContactInfo,
    ContactMessage, 
    FAQ, 
    Partner,
    Testimonial,
    PrivacyPolicy,  # Add this
    TermsOfService, # Add this
)

# ===========================
# Admin Branding → MELTSA_TATU
# ===========================

admin.site.site_header = "MELTSA_TATU Administration"
admin.site.site_title = "MELTSA_TATU Portal"
admin.site.index_title = "MELTSA_TATU Dashboard"


# ===========================
# Privacy Policy Admin
# ===========================

@admin.register(PrivacyPolicy)
class PrivacyPolicyAdmin(admin.ModelAdmin):
    list_display = ('title', 'version', 'effective_date', 'is_current', 'created_at')
    list_filter = ('is_current', 'effective_date')
    search_fields = ('title', 'version', 'content')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Policy Information', {
            'fields': ('title', 'version', 'effective_date', 'is_current')
        }),
        ('Content', {
            'fields': ('content',),
            'classes': ('wide',),
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
 

# ===========================
# Terms of Service Admin
# ===========================

@admin.register(TermsOfService)
class TermsOfServiceAdmin(admin.ModelAdmin):
    list_display = ('title', 'version', 'effective_date', 'is_current', 'created_at')
    list_filter = ('is_current', 'effective_date')
    search_fields = ('title', 'version', 'content')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Terms Information', {
            'fields': ('title', 'version', 'effective_date', 'is_current')
        }),
        ('Content', {
            'fields': ('content',),
            'classes': ('wide',),
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# ===========================
# About Admin
# ===========================

@admin.register(About)
class AboutAdmin(admin.ModelAdmin):
    list_display = ['title', 'established_year', 'total_members', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'subtitle', 'established_year')
        }),
        ('Content', {
            'fields': ('mission', 'vision', 'history', 'core_values')
        }),
        ('Statistics', {
            'fields': ('total_members', 'total_executives', 'total_events')
        }),
        ('Media', {
            'fields': ('featured_image', 'mission_image')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description')
        }),
        ('Metadata', {
            'fields': ('updated_by', 'created_at', 'updated_at')
        }),
    )


# ===========================
# Executive Team Admin
# ===========================

@admin.register(ExecutiveTeam)
class ExecutiveTeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'position_display', 'order', 'is_active']
    list_filter = ['position', 'is_active']
    list_editable = ['order', 'is_active']
    search_fields = ['name', 'bio']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'position', 'custom_position', 'image', 'bio')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone')
        }),
        ('Social Media Links', {
            'fields': (
                'facebook_url', 'twitter_url', 'instagram_url',
                'linkedin_url', 'whatsapp_url', 'website_url'
            ),
            'classes': ('wide',),
            'description': 'Enter full URLs including https://'
        }),
        ('Settings', {
            'fields': ('order', 'is_active', 'joined_date')
        }),
    )
    
    def position_display(self, obj):
        return obj.position_display
    position_display.short_description = 'Position'


@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    list_display = ['primary_email', 'primary_phone', 'city', 'updated_at']
    readonly_fields = ['updated_at']


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'email', 'subject', 'message']
    readonly_fields = ['ip_address', 'user_agent', 'created_at']
    
    def mark_as_replied(self, request, queryset):
        queryset.update(status='replied')
    mark_as_replied.short_description = "Mark selected as replied"
    
    actions = [mark_as_replied]


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question', 'category', 'order', 'is_active', 'is_featured']
    list_filter = ['category', 'is_active', 'is_featured']
    list_editable = ['order', 'is_active', 'is_featured']
    search_fields = ['question', 'answer']


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ['name', 'logo_preview', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    
    def logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" style="max-height: 30px;" />', obj.logo.url)
        return '-'
    logo_preview.short_description = 'Logo'


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ['student_name', 'student_level', 'rating', 'order', 'is_active']
    list_filter = ['rating', 'is_active']
    list_editable = ['order', 'is_active']




# ===========================
# Academic Setting Admin
# ===========================

@admin.register(AcademicSetting)
class AcademicSettingAdmin(admin.ModelAdmin):
    list_display = ("academic_year", "current_semester", "is_active", "updated_by", "updated_at")
    list_filter = ("is_active", "current_semester")
    search_fields = ("academic_year",)


# ===========================
# Announcement Admin
# ===========================

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "created_by", "created_at", "is_active")
    list_filter = ("is_active", "created_at")
    search_fields = ("title", "subject")
    readonly_fields = ("created_at", "updated_at")


# ===========================
# Notification Admin
# ===========================

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "notification_type", "created_by", "created_at", "expires_at", "is_global")
    list_filter = ("notification_type", "is_global")
    search_fields = ("title", "message")


# ===========================
# Blog Post Admin
# ===========================

@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "published", "views", "created_at")
    list_filter = ("published",)
    search_fields = ("title", "content")
    readonly_fields = ("views",)


# ===========================
# Video Vlog Admin
# ===========================

@admin.register(VideoVlog)
class VideoVlogAdmin(admin.ModelAdmin):
    list_display = ("title", "uploaded_by", "views", "uploaded_at")
    search_fields = ("title", "description")
    readonly_fields = ("views",)


# ===========================
# Student Executive Admin
# ===========================

@admin.register(StudentExecutive)
class StudentExecutiveAdmin(admin.ModelAdmin):
    list_display = ("user", "position", "executive_year", "is_active")
    list_filter = ("position", "is_active")
    search_fields = ("user__username", "user__first_name", "user__last_name")


# ===========================
# Student Document Admin
# ===========================

@admin.register(StudentDocument)
class StudentDocumentAdmin(admin.ModelAdmin):
    list_display = ("student", "title", "document_type", "uploaded_at")
    list_filter = ("document_type",)
    search_fields = ("title", "student__username")
    readonly_fields = ("uploaded_at",)