# apps/payments/admin.py

from django.contrib import admin
from .models import Due, Payment, PaymentHistory

# ===============================
# Payment History Inline
# ===============================
class PaymentHistoryInline(admin.TabularInline):
    model = PaymentHistory
    extra = 0
    readonly_fields = ('status', 'notes', 'created_at')
    can_delete = False

# ===============================
# Payment Admin
# ===============================
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'student',
        'due',
        'amount',
        'status',
        'reference',
        'paystack_reference',
        'paid_at',
        'created_at',
        'get_due_type',
    )
    list_filter = ('status', 'due__due_type', 'created_at')
    search_fields = (
        'student__username',
        'student__student_id',
        'reference',
        'paystack_reference',
        'due__title'
    )
    readonly_fields = ('created_at', 'paid_at')
    inlines = [PaymentHistoryInline]

    def get_due_type(self, obj):
        return obj.due.due_type
    get_due_type.short_description = "Due Type"

# ===============================
# Due Admin
# ===============================
@admin.register(Due)
class DueAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'due_type',
        'amount',
        'academic_setting',
        'deadline',
        'is_active',
        'created_by',
        'created_at',
        'get_total_paid',
        'get_total_students',
        'get_paid_students',
    )
    list_filter = ('due_type', 'is_active', 'academic_setting')
    search_fields = ('title', 'description', 'created_by__username')
    readonly_fields = ('created_at',)
    
    def get_total_paid(self, obj):
        return obj.get_total_paid()
    get_total_paid.short_description = "Total Paid (GHS)"
    
    def get_total_students(self, obj):
        return obj.get_total_students()
    get_total_students.short_description = "Target Students"
    
    def get_paid_students(self, obj):
        return obj.get_paid_students()
    get_paid_students.short_description = "Paid Students"

# ===============================
# PaymentHistory Admin
# ===============================
@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ('payment', 'status', 'notes', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('payment__reference', 'payment__student__username', 'notes')
    readonly_fields = ('created_at',)