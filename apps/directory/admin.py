from django.contrib import admin
from django.utils.html import format_html
from .models import (
    StudentIDCard,
    PastQuestion,        # Add this
    StudentHandbook,      # Add this
    AcademicCalendar,     # Add this
)


# ===========================
# Past Question Admin
# ===========================

@admin.register(PastQuestion)
class PastQuestionAdmin(admin.ModelAdmin):
    list_display = ('course_code', 'title', 'level', 'semester', 'exam_year', 'downloads', 'is_approved', 'is_active')
    list_filter = ('level', 'semester', 'exam_year', 'is_approved', 'is_active')
    search_fields = ('course_code', 'course_name', 'title')
    readonly_fields = ('file_size', 'downloads', 'views', 'uploaded_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('course_code', 'course_name', 'title', 'level', 'semester')
        }),
        ('Year Information', {
            'fields': ('academic_year', 'exam_year')
        }),
        ('File', {
            'fields': ('file', 'file_size')
        }),
        ('Status', {
            'fields': ('is_approved', 'is_active')
        }),
        ('Statistics', {
            'fields': ('downloads', 'views'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('uploaded_by', 'uploaded_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['approve_selected', 'disapprove_selected']
    
    def approve_selected(self, request, queryset):
        queryset.update(is_approved=True)
    approve_selected.short_description = "Approve selected past questions"
    
    def disapprove_selected(self, request, queryset):
        queryset.update(is_approved=False)
    disapprove_selected.short_description = "Disapprove selected past questions"


# ===========================
# Student Handbook Admin
# ===========================

@admin.register(StudentHandbook)
class StudentHandbookAdmin(admin.ModelAdmin):
    list_display = ('title', 'version', 'is_current', 'effective_date', 'downloads', 'views')
    list_filter = ('is_current', 'effective_date')
    search_fields = ('title', 'description')
    readonly_fields = ('file_size', 'downloads', 'views', 'uploaded_at', 'updated_at')
    fieldsets = (
        ('Handbook Information', {
            'fields': ('title', 'version', 'description', 'is_current', 'effective_date')
        }),
        ('Media', {
            'fields': ('cover_image', 'file', 'file_size')
        }),
        ('Statistics', {
            'fields': ('downloads', 'views'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('uploaded_by', 'uploaded_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)
    
    def cover_preview(self, obj):
        if obj.cover_image:
            return format_html('<img src="{}" style="max-height: 50px;" />', obj.cover_image.url)
        return '-'
    cover_preview.short_description = 'Cover'


# ===========================
# Academic Calendar Admin
# ===========================

@admin.register(AcademicCalendar)
class AcademicCalendarAdmin(admin.ModelAdmin):
    list_display = ('title', 'event_type', 'start_date', 'end_date', 'academic_year', 'is_important', 'is_active')
    list_filter = ('event_type', 'academic_year', 'semester', 'level', 'is_important', 'is_active')
    search_fields = ('title', 'description', 'venue')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Event Information', {
            'fields': ('title', 'event_type', 'description', 'is_important', 'is_active')
        }),
        ('Date and Time', {
            'fields': ('start_date', 'end_date', 'is_all_day', 'start_time', 'end_time')
        }),
        ('Academic Context', {
            'fields': ('academic_year', 'semester', 'level', 'venue')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['mark_important', 'mark_not_important', 'activate_selected', 'deactivate_selected']
    
    def mark_important(self, request, queryset):
        queryset.update(is_important=True)
    mark_important.short_description = "Mark selected as important"
    
    def mark_not_important(self, request, queryset):
        queryset.update(is_important=False)
    mark_not_important.short_description = "Mark selected as not important"
    
    def activate_selected(self, request, queryset):
        queryset.update(is_active=True)
    activate_selected.short_description = "Activate selected events"
    
    def deactivate_selected(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_selected.short_description = "Deactivate selected events"


# ===========================
# Student ID Card Admin (Existing)
# ===========================

@admin.register(StudentIDCard)
class StudentIDCardAdmin(admin.ModelAdmin):
    list_display = (
        'student_info', 
        'card_number', 
        'blood_group', 
        'valid_until', 
        'emergency_contact', 
        'signature_status',
        'download_count',
        'issued_at'
    )
    list_filter = ('blood_group', 'valid_until', 'issued_at')
    search_fields = (
        'student__username', 
        'student__first_name', 
        'student__last_name', 
        'student__student_id',
        'card_number',
        'emergency_contact_name',
        'emergency_phone'
    )
    readonly_fields = (
        'qr_code_preview', 
        'signature_preview',
        'issued_at', 
        'last_downloaded', 
        'download_count',
        'card_number'
    )
    fieldsets = (
        ('Student Information', {
            'fields': ('student', 'card_number')
        }),
        ('Front of Card', {
            'fields': ('blood_group', 'valid_until', 'student_signature', 'signature_preview', 'qr_code_preview', 'qr_code', 'issued_at'),
            'description': 'Information displayed on the front of the ID card'
        }),
        ('Emergency Contact (Back of Card)', {
            'fields': ('emergency_contact_name', 'emergency_relationship', 'emergency_phone', 'emergency_address'),
            'description': 'Emergency contact information displayed on the back'
        }),
        ('Medical Information (Back of Card)', {
            'fields': ('allergies', 'medical_conditions'),
            'description': 'Important medical information'
        }),
        ('Tracking', {
            'fields': ('download_count', 'last_downloaded'),
            'classes': ('collapse',)
        }),
    )
    
    def student_info(self, obj):
        """Display student name and ID"""
        return format_html(
            '{}<br><small style="color: #666;">{}</small>',
            obj.student.get_full_name() or obj.student.username,
            obj.student.student_id or 'No ID'
        )
    student_info.short_description = 'Student'
    student_info.admin_order_field = 'student__last_name'
    
    def emergency_contact(self, obj):
        """Display emergency contact summary"""
        if obj.emergency_contact_name and obj.emergency_phone:
            return format_html(
                '{}<br><small style="color: #666;">{}</small>',
                obj.emergency_contact_name,
                obj.emergency_phone
            )
        return '-'
    emergency_contact.short_description = 'Emergency Contact'
    
    def signature_status(self, obj):
        """Display signature status with preview link"""
        if obj.student_signature:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓</span> '
                '<a href="{}" target="_blank" style="font-size: 11px;">View</a>',
                obj.student_signature.url
            )
        return format_html('<span style="color: #ccc;">✗</span>')
    signature_status.short_description = 'Signature'
    
    def signature_preview(self, obj):
        """Display signature preview"""
        if obj.student_signature:
            return format_html(
                '<img src="{}" style="max-height: 60px; max-width: 150px; border: 1px solid #ddd; padding: 8px; background: #f9f9f9; border-radius: 4px;" />',
                obj.student_signature.url
            )
        return format_html(
            '<div style="padding: 15px; background: #f8f9fa; border: 1px dashed #ccc; border-radius: 4px; color: #666; text-align: center;">'
            '<i class="fas fa-pen" style="font-size: 24px; margin-bottom: 5px; display: block;"></i>'
            'No signature uploaded'
            '</div>'
        )
    signature_preview.short_description = 'Signature Preview'
    
    def qr_code_preview(self, obj):
        """Display QR code preview"""
        if obj.qr_code:
            return format_html(
                '<img src="{}" style="width: 100px; height: 100px; border: 1px solid #ddd; padding: 5px; background: white;" /><br>'
                '<small style="color: #666;">Click regenerate action to update</small>',
                obj.qr_code.url
            )
        return format_html(
            '<div style="padding: 20px; background: #f8f9fa; border: 1px dashed #ccc; border-radius: 4px; color: #666;">'
            'No QR code generated'
            '</div>'
        )
    qr_code_preview.short_description = 'QR Code Preview'
    
    actions = ['regenerate_qr_codes', 'reset_download_counts', 'clear_signatures']
    
    def regenerate_qr_codes(self, request, queryset):
        """Regenerate QR codes for selected ID cards"""
        count = 0
        for id_card in queryset:
            id_card.generate_qr_code()
            id_card.save()
            count += 1
        self.message_user(request, f"QR codes regenerated for {count} ID card(s).")
    regenerate_qr_codes.short_description = "♻️ Regenerate QR codes for selected cards"
    
    def reset_download_counts(self, request, queryset):
        """Reset download counts to zero"""
        count = queryset.update(download_count=0)
        self.message_user(request, f"Download counts reset for {count} ID card(s).")
    reset_download_counts.short_description = "📊 Reset download counts"
    
    def clear_signatures(self, request, queryset):
        """Clear signatures from selected ID cards"""
        count = queryset.update(student_signature=None)
        self.message_user(request, f"Signatures cleared from {count} ID card(s).")
    clear_signatures.short_description = "❌ Clear signatures"
    
    # Add inline actions for individual cards
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:pk>/regenerate-qr/',
                self.admin_site.admin_view(self.regenerate_single_qr),
                name='directory_studentidcard_regenerate_qr',
            ),
            path(
                '<int:pk>/clear-signature/',
                self.admin_site.admin_view(self.clear_single_signature),
                name='directory_studentidcard_clear_signature',
            ),
        ]
        return custom_urls + urls
    
    def regenerate_single_qr(self, request, pk):
        """Regenerate QR code for a single ID card"""
        from django.shortcuts import get_object_or_404, redirect
        from django.contrib import messages
        
        id_card = get_object_or_404(StudentIDCard, pk=pk)
        id_card.generate_qr_code()
        id_card.save()
        
        messages.success(request, f"QR code regenerated for {id_card.student.get_full_name()}")
        return redirect('admin:directory_studentidcard_change', id_card.pk)
    
    def clear_single_signature(self, request, pk):
        """Clear signature for a single ID card"""
        from django.shortcuts import get_object_or_404, redirect
        from django.contrib import messages
        
        id_card = get_object_or_404(StudentIDCard, pk=pk)
        id_card.student_signature = None
        id_card.save()
        
        messages.success(request, f"Signature cleared for {id_card.student.get_full_name()}")
        return redirect('admin:directory_studentidcard_change', id_card.pk)


# StudentIDCardInline for User admin
class StudentIDCardInline(admin.TabularInline):
    model = StudentIDCard
    extra = 0
    fields = ('card_number', 'blood_group', 'valid_until', 'signature_status', 'download_count', 'last_downloaded')
    readonly_fields = ('card_number', 'signature_status', 'download_count', 'last_downloaded')
    can_delete = False
    verbose_name = "ID Card"
    verbose_name_plural = "ID Cards"
    
    def signature_status(self, obj):
        if obj.student_signature:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: #ccc;">✗</span>')
    signature_status.short_description = 'Signature'