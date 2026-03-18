# payments/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
import re
from datetime import date, timedelta

from .models import Due, Payment, PaymentHistory
from apps.accounts.models import User
from apps.core.models import AcademicSetting


# ========== DUE MANAGEMENT FORMS ==========

class DueForm(forms.ModelForm):
    """
    Form for creating and editing dues
    """
    target_levels = forms.MultipleChoiceField(
        choices=User._meta.get_field('level').choices,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=True,
        help_text="Select which levels this due applies to"
    )
    
    class Meta:
        model = Due
        fields = (
            'title', 'description', 'amount', 'due_type', 'deadline', 
            'academic_setting', 'is_active'
        )
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Academic Dues 2024/2025'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Detailed description of the due...'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'due_type': forms.Select(attrs={'class': 'form-select'}),
            'deadline': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'academic_setting': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Only show active academic settings
        self.fields['academic_setting'].queryset = AcademicSetting.objects.all()
        
        # Pre-populate target_levels if editing
        if self.instance and self.instance.pk:
            self.fields['target_levels'].initial = self.instance.target_levels
    
    def clean_amount(self):
        """Validate amount"""
        amount = self.cleaned_data.get('amount')
        
        if amount <= 0:
            raise ValidationError("Amount must be greater than zero.")
        
        if amount > 1000000:  # 1 million limit
            raise ValidationError("Amount cannot exceed ₦1,000,000.")
        
        return amount
    
    def clean_deadline(self):
        """Validate deadline"""
        deadline = self.cleaned_data.get('deadline')
        
        if deadline and deadline < date.today():
            raise ValidationError("Deadline cannot be in the past.")
        
        return deadline
    
    def save(self, commit=True):
        due = super().save(commit=False)
        
        # Convert target_levels from list to JSON field
        due.target_levels = self.cleaned_data['target_levels']
        
        if commit:
            due.save()
        
        return due


class DueUpdateForm(forms.ModelForm):
    """
    Form for updating due (without changing amount after payments started)
    """
    target_levels = forms.MultipleChoiceField(
        choices=User._meta.get_field('level').choices,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=True
    )
    
    class Meta:
        model = Due
        fields = (
            'title', 'description', 'deadline', 'due_type',
            'academic_setting', 'is_active'
        )
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'due_type': forms.Select(attrs={'class': 'form-select'}),
            'deadline': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'academic_setting': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Check if there are any successful payments
        if self.instance and self.instance.pk:
            has_payments = Payment.objects.filter(
                due=self.instance,
                status='success'
            ).exists()
            
            if has_payments:
                # Show amount as read-only field
                self.fields['amount_display'] = forms.DecimalField(
                    initial=self.instance.amount,
                    disabled=True,
                    widget=forms.NumberInput(attrs={'class': 'form-control'}),
                    label="Amount",
                    help_text="Amount cannot be changed after payments have been made."
                )
            
            self.fields['target_levels'].initial = self.instance.target_levels
    
    def save(self, commit=True):
        due = super().save(commit=False)
        due.target_levels = self.cleaned_data['target_levels']
        
        if commit:
            due.save()
        
        return due


class DueFilterForm(forms.Form):
    """
    Form for filtering dues list
    """
    academic_setting = forms.ModelChoiceField(
        queryset=AcademicSetting.objects.all(),
        required=False,
        empty_label="All Academic Years",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    due_type = forms.ChoiceField(
        choices=[('', 'All Types')] + list(Due.DUE_TYPES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=[
            ('', 'All'),
            ('active', 'Active Only'),
            ('inactive', 'Inactive Only'),
            ('upcoming', 'Upcoming'),
            ('expired', 'Expired'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by title...'
        })
    )
    sort_by = forms.ChoiceField(
        choices=[
            ('-created_at', 'Newest First'),
            ('created_at', 'Oldest First'),
            ('deadline', 'Deadline (Earliest)'),
            ('-deadline', 'Deadline (Latest)'),
            ('amount', 'Amount (Low to High)'),
            ('-amount', 'Amount (High to Low)'),
        ],
        required=False,
        initial='-created_at',
        widget=forms.Select(attrs={'class': 'form-select'})
    )


# ========== PAYMENT PROCESSING FORMS ==========

class PaymentInitiationForm(forms.Form):
    """
    Form for initiating a payment
    """
    due_id = forms.IntegerField(widget=forms.HiddenInput())
    amount = forms.DecimalField(widget=forms.HiddenInput())
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'readonly': True
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.student = kwargs.pop('student', None)
        super().__init__(*args, **kwargs)
        
        if self.student:
            self.fields['email'].initial = self.student.email
            self.fields['email'].widget.attrs['readonly'] = True
    
    def clean(self):
        cleaned_data = super().clean()
        due_id = cleaned_data.get('due_id')
        
        if due_id and self.student:
            try:
                due = Due.objects.get(id=due_id, is_active=True)
                
                # Check if already paid
                if Payment.objects.filter(
                    student=self.student,
                    due=due,
                    status='success'
                ).exists():
                    raise ValidationError("You have already paid this due.")
                
                # Check deadline
                if due.deadline < date.today():
                    raise ValidationError("Payment deadline has passed.")
                
                # Check if student level is targeted
                if self.student.level not in due.target_levels:
                    raise ValidationError("This due is not applicable to your level.")
                
            except Due.DoesNotExist:
                raise ValidationError("Invalid due selected.")
        
        return cleaned_data


class PaystackPaymentForm(forms.Form):
    """
    Form for Paystack payment processing (used in template)
    """
    reference = forms.CharField(max_length=100, widget=forms.HiddenInput())
    amount = forms.DecimalField(widget=forms.HiddenInput())
    email = forms.EmailField(widget=forms.HiddenInput())
    public_key = forms.CharField(widget=forms.HiddenInput())
    callback_url = forms.URLField(widget=forms.HiddenInput())


# ========== PAYMENT VERIFICATION FORMS ==========

class PaymentVerificationForm(forms.Form):
    """
    Form for verifying payment
    """
    reference = forms.CharField(max_length=100, required=True)
    due_id = forms.IntegerField(required=True)
    
    def clean_reference(self):
        reference = self.cleaned_data.get('reference')
        
        # Check if reference already exists
        if Payment.objects.filter(reference=reference).exists():
            raise ValidationError("Payment reference already exists.")
        
        return reference


class ManualPaymentVerificationForm(forms.Form):
    """
    Form for manually verifying payments (admin/staff only)
    """
    payment_id = forms.IntegerField(widget=forms.HiddenInput())
    status = forms.ChoiceField(
        choices=Payment.PAYMENT_STATUS,  # Use the correct attribute name
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        required=True
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Add notes about this verification (optional)'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        payment_id = cleaned_data.get('payment_id')
        status = cleaned_data.get('status')
        
        if payment_id:
            try:
                payment = Payment.objects.get(id=payment_id)
                
                if payment.status != 'pending':
                    raise ValidationError(f"This payment is already {payment.get_status_display()}.")
                
            except Payment.DoesNotExist:
                raise ValidationError("Payment not found.")
        
        return cleaned_data


# ========== PAYMENT SEARCH AND FILTER FORMS ==========

class PaymentSearchForm(forms.Form):
    """
    Form for searching and filtering payments (admin/staff)
    """
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by student name, ID, or reference...'
        })
    )
    due = forms.ModelChoiceField(
        queryset=Due.objects.all(),
        required=False,
        empty_label="All Dues",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + list(Payment.PAYMENT_STATUS),  # Fixed: use PAYMENT_STATUS
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    level = forms.ChoiceField(
        choices=[('', 'All Levels')] + list(User._meta.get_field('level').choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    sort_by = forms.ChoiceField(
        choices=[
            ('-created_at', 'Newest First'),
            ('created_at', 'Oldest First'),
            ('-amount', 'Amount (High to Low)'),
            ('amount', 'Amount (Low to High)'),
            ('student__level', 'Level'),
        ],
        required=False,
        initial='-created_at',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise ValidationError("Start date cannot be after end date.")
        
        return cleaned_data


class StudentPaymentHistoryForm(forms.Form):
    """
    Form for students to filter their payment history
    """
    due = forms.ModelChoiceField(
        queryset=Due.objects.all(),
        required=False,
        empty_label="All Dues",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + list(Payment.PAYMENT_STATUS),  # Fixed: use PAYMENT_STATUS
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    def __init__(self, *args, **kwargs):
        self.student = kwargs.pop('student', None)
        super().__init__(*args, **kwargs)
        
        if self.student:
            # Only show dues that are applicable to this student's level
            self.fields['due'].queryset = Due.objects.filter(
                is_active=True
            ).exclude(
                ~Q(target_levels__contains=[self.student.level])
            )


# ========== ADMIN REPORT FORMS ==========

class PaymentReportForm(forms.Form):
    """
    Form for generating payment reports
    """
    REPORT_TYPES = (
        ('summary', 'Summary Report'),
        ('detailed', 'Detailed Report'),
        ('by_level', 'Report by Level'),
        ('by_due', 'Report by Due Type'),
        ('outstanding', 'Outstanding Payments'),
    )
    
    report_type = forms.ChoiceField(
        choices=REPORT_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    academic_setting = forms.ModelChoiceField(
        queryset=AcademicSetting.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    due = forms.ModelChoiceField(
        queryset=Due.objects.all(),
        required=False,
        empty_label="All Dues",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    level = forms.ChoiceField(
        choices=[('', 'All Levels')] + list(User._meta.get_field('level').choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    format = forms.ChoiceField(
        choices=[
            ('html', 'HTML View'),
            ('csv', 'CSV Export'),
            ('pdf', 'PDF Export'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True,
        initial='html'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        report_type = cleaned_data.get('report_type')
        due = cleaned_data.get('due')
        
        if report_type == 'by_due' and not due:
            raise ValidationError("Please select a due for this report type.")
        
        return cleaned_data


class OutstandingPaymentsForm(forms.Form):
    """
    Form for viewing outstanding payments
    """
    due = forms.ModelChoiceField(
        queryset=Due.objects.filter(is_active=True),
        required=True,
        empty_label="Select Due",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    level = forms.ChoiceField(
        choices=[('', 'All Levels')] + list(User._meta.get_field('level').choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Only show dues with future deadlines
        self.fields['due'].queryset = Due.objects.filter(
            is_active=True,
            deadline__gte=date.today()
        )


# ========== BULK OPERATIONS FORMS ==========

class BulkDueAssignmentForm(forms.Form):
    """
    Form for assigning dues to multiple levels
    """
    due = forms.ModelChoiceField(
        queryset=Due.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    levels = forms.MultipleChoiceField(
        choices=User._meta.get_field('level').choices,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=True
    )
    
    def clean(self):
        cleaned_data = super().clean()
        due = cleaned_data.get('due')
        levels = cleaned_data.get('levels')
        
        if due and levels:
            due.target_levels = levels
            due.save()
        
        return cleaned_data


class BulkPaymentStatusUpdateForm(forms.Form):
    """
    Form for bulk updating payment status (admin only)
    """
    ACTION_CHOICES = (
        ('mark_success', 'Mark as Successful'),
        ('mark_failed', 'Mark as Failed'),
        ('mark_pending', 'Mark as Pending'),
    )
    
    payment_ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=True
    )
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Reason for bulk update (optional)'
        })
    )
    
    def clean_payment_ids(self):
        ids = self.cleaned_data.get('payment_ids')
        try:
            id_list = [int(id.strip()) for id in ids.split(',') if id.strip()]
            return id_list
        except ValueError:
            raise ValidationError("Invalid payment IDs provided.")


# ========== EXECUTIVE EXEMPTION FORMS ==========

class ExecutiveExemptionForm(forms.Form):
    """
    Form for managing executive exemptions (admin only)
    """
    due = forms.ModelChoiceField(
        queryset=Due.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    executives = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(user_type='executive', is_active=True),
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 10}),
        required=True,
        help_text="Select executives to exempt from this due"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        due = cleaned_data.get('due')
        executives = cleaned_data.get('executives')
        
        if due and executives:
            # Check if any executive has already paid
            paid_execs = Payment.objects.filter(
                student__in=executives,
                due=due,
                status='success'
            ).values_list('student_id', flat=True)
            
            if paid_execs:
                paid_names = User.objects.filter(
                    id__in=paid_execs
                ).values_list('get_full_name', flat=True)
                
                raise ValidationError(
                    f"The following executives have already paid and cannot be exempted: "
                    f"{', '.join(paid_names)}"
                )
        
        return cleaned_data


# ========== REMINDER FORM ==========

class PaymentReminderForm(forms.Form):
    """
    Form for sending payment reminders
    """
    due = forms.ModelChoiceField(
        queryset=Due.objects.filter(is_active=True, deadline__gte=date.today()),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    recipient_type = forms.ChoiceField(
        choices=[
            ('all', 'All Outstanding Students'),
            ('level', 'Specific Level'),
            ('custom', 'Custom List'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        required=True
    )
    level = forms.ChoiceField(
        choices=[('', 'Select Level')] + list(User._meta.get_field('level').choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    custom_emails = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter email addresses (one per line)'
        })
    )
    message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Additional message (optional)'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        recipient_type = cleaned_data.get('recipient_type')
        level = cleaned_data.get('level')
        custom_emails = cleaned_data.get('custom_emails')
        
        if recipient_type == 'level' and not level:
            raise ValidationError("Please select a level.")
        
        if recipient_type == 'custom' and not custom_emails:
            raise ValidationError("Please enter email addresses.")
        
        return cleaned_data
    
    def get_recipient_emails(self):
        """Get list of recipient emails based on form data"""
        from django.db.models import Q
        
        cleaned_data = self.cleaned_data
        due = cleaned_data.get('due')
        recipient_type = cleaned_data.get('recipient_type')
        
        if recipient_type == 'all':
            # Get all students who haven't paid
            paid_students = Payment.objects.filter(
                due=due,
                status='success'
            ).values_list('student_id', flat=True)
            
            students = User.objects.filter(
                user_type='student',
                level__in=due.target_levels,
                is_active=True
            ).exclude(id__in=paid_students)
            
            return students.values_list('email', flat=True)
        
        elif recipient_type == 'level':
            level = cleaned_data.get('level')
            paid_students = Payment.objects.filter(
                due=due,
                status='success'
            ).values_list('student_id', flat=True)
            
            students = User.objects.filter(
                user_type='student',
                level=level,
                is_active=True
            ).exclude(id__in=paid_students)
            
            return students.values_list('email', flat=True)
        
        elif recipient_type == 'custom':
            emails = [email.strip() for email in cleaned_data.get('custom_emails').split('\n') if email.strip()]
            return emails
        
        return []


# ========== PAYSTACK INTEGRATION FORM ==========

class PaystackSettingsForm(forms.Form):
    """
    Form for Paystack settings (admin only)
    """
    public_key = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'pk_test_... or pk_live_...'
        }),
        required=True,
        help_text="Your Paystack public key"
    )
    secret_key = forms.CharField(
        max_length=100,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'sk_test_... or sk_live_...'
        }),
        required=True,
        help_text="Your Paystack secret key"
    )
    webhook_url = forms.URLField(
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'readonly': True
        }),
        required=False,
        help_text="Configure this URL in your Paystack dashboard for webhooks"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set webhook URL from settings
        self.fields['webhook_url'].initial = f"{settings.SITE_URL}/payments/webhook/"
    
    def clean_public_key(self):
        key = self.cleaned_data.get('public_key')
        if not key.startswith(('pk_test_', 'pk_live_')):
            raise ValidationError("Invalid Paystack public key format.")
        return key
    
    def clean_secret_key(self):
        key = self.cleaned_data.get('secret_key')
        if not key.startswith(('sk_test_', 'sk_live_')):
            raise ValidationError("Invalid Paystack secret key format.")
        return key