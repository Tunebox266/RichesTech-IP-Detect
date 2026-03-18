# events/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta
import re

from .models import (
    Event, EventAttendee, AttendanceSession, 
    AttendanceRecord, AttendanceCode, EventFeedback
)
from apps.accounts.models import User


# ========== EVENT MANAGEMENT FORMS ==========

class EventForm(forms.ModelForm):
    """
    Form for creating and editing events
    """
    class Meta:
        model = Event
        fields = (
            'title', 'description', 'event_type', 'start_date', 'end_date',
            'venue', 'poster', 'max_attendees', 'requires_attendance_tracking',
            'is_active'
        )
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter event title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Detailed description of the event...'
            }),
            'event_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'end_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'venue': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Event venue/location'
            }),
            'poster': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'max_attendees': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'placeholder': 'Leave blank for unlimited'
            }),
            'requires_attendance_tracking': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if end_date <= start_date:
                raise ValidationError("End date must be after start date.")
            
            if start_date < timezone.now():
                raise ValidationError("Start date cannot be in the past.")
        
        return cleaned_data
    
    def clean_poster(self):
        poster = self.cleaned_data.get('poster')
        
        if poster:
            # Check file size (max 5MB)
            if poster.size > 5 * 1024 * 1024:
                raise ValidationError("Poster image must be less than 5MB.")
            
            # Check file extension
            ext = poster.name.split('.')[-1].lower()
            if ext not in ['jpg', 'jpeg', 'png', 'gif']:
                raise ValidationError("Please upload a valid image file (jpg, jpeg, png, gif).")
        
        return poster


class EventUpdateForm(forms.ModelForm):
    """
    Form for updating event details (with restrictions after registrations)
    """
    class Meta:
        model = Event
        fields = (
            'title', 'description', 'event_type', 'start_date', 'end_date',
            'venue', 'poster', 'max_attendees', 'requires_attendance_tracking',
            'is_active'
        )
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'event_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'venue': forms.TextInput(attrs={'class': 'form-control'}),
            'poster': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'max_attendees': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'requires_attendance_tracking': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Check if there are registrations
        if self.instance and self.instance.pk:
            has_registrations = self.instance.attendees.exists()
            
            if has_registrations:
                # Disable fields that shouldn't be changed after registrations
                self.fields['max_attendees'].disabled = True
                self.fields['max_attendees'].help_text = "Cannot be changed after registrations have started."
                
                self.fields['requires_attendance_tracking'].disabled = True
                self.fields['requires_attendance_tracking'].help_text = "Cannot be changed after registrations have started."
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date <= start_date:
            raise ValidationError("End date must be after start date.")
        
        # Check if event has started
        if self.instance and self.instance.start_date < timezone.now():
            if start_date != self.instance.start_date:
                raise ValidationError("Cannot change start date after event has started.")
        
        return cleaned_data


class EventSearchForm(forms.Form):
    """
    Form for searching and filtering events
    """
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search events...'
        })
    )
    event_type = forms.ChoiceField(
        choices=[('', 'All Types')] + list(Event.EVENT_TYPES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_filter = forms.ChoiceField(
        choices=[
            ('', 'All'),
            ('today', 'Today'),
            ('tomorrow', 'Tomorrow'),
            ('this_week', 'This Week'),
            ('this_month', 'This Month'),
            ('next_month', 'Next Month'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    venue = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filter by venue...'
        })
    )
    sort_by = forms.ChoiceField(
        choices=[
            ('-start_date', 'Date (Newest)'),
            ('start_date', 'Date (Oldest)'),
            ('title', 'Title (A-Z)'),
            ('-title', 'Title (Z-A)'),
        ],
        required=False,
        initial='-start_date',
        widget=forms.Select(attrs={'class': 'form-select'})
    )


# ========== EVENT REGISTRATION FORMS ==========

class EventRegistrationForm(forms.Form):
    """
    Form for registering for an event
    """
    terms_accepted = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        error_messages={'required': 'You must accept the terms and conditions to register.'}
    )
    
    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('event', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.event:
            # Add event-specific questions or fields here
            pass
    
    def clean(self):
        cleaned_data = super().clean()
        
        if self.event and self.user:
            # Check if already registered
            if EventAttendee.objects.filter(event=self.event, user=self.user).exists():
                raise ValidationError("You are already registered for this event.")
            
            # Check if event is full
            if self.event.is_full():
                raise ValidationError("This event is already full.")
            
            # Check if event has started
            if self.event.start_date < timezone.now():
                raise ValidationError("This event has already started.")
        
        return cleaned_data


class BulkRegistrationForm(forms.Form):
    """
    Form for bulk registering students (admin/staff only)
    """
    students = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(user_type='student', is_active=True),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'size': 15
        }),
        required=True
    )
    
    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('event', None)
        super().__init__(*args, **kwargs)
        
        if self.event:
            # Exclude already registered students
            registered_ids = self.event.attendees.values_list('user_id', flat=True)
            self.fields['students'].queryset = User.objects.filter(
                user_type='student',
                is_active=True
            ).exclude(id__in=registered_ids)
    
    def clean(self):
        cleaned_data = super().clean()
        students = cleaned_data.get('students')
        
        if self.event and students:
            # Check capacity
            current_count = self.event.get_attendee_count()
            new_count = len(students)
            
            if self.event.max_attendees and (current_count + new_count) > self.event.max_attendees:
                raise ValidationError(
                    f"Cannot add {new_count} students. Only {self.event.max_attendees - current_count} spots available."
                )
        
        return cleaned_data


# ========== ATTENDANCE SESSION FORMS ==========

class AttendanceSessionForm(forms.ModelForm):
    """
    Form for creating attendance sessions
    """
    class Meta:
        model = AttendanceSession
        fields = ('name', 'session_type', 'start_time', 'end_time', 'venue', 'is_active')
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Day 1 Morning Session'
            }),
            'session_type': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'end_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'venue': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Session venue (optional)'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('event', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time and end_time <= start_time:
            raise ValidationError("End time must be after start time.")
        
        # Check if session times are within event timeframe
        if self.event and start_time and end_time:
            if start_time < self.event.start_date:
                raise ValidationError("Session cannot start before the event.")
            
            if end_time > self.event.end_date:
                raise ValidationError("Session cannot end after the event.")
        
        return cleaned_data


class AttendanceSessionUpdateForm(forms.ModelForm):
    """
    Form for updating attendance sessions
    """
    class Meta:
        model = AttendanceSession
        fields = ('name', 'session_type', 'start_time', 'end_time', 'venue', 'is_active')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'session_type': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'venue': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time and end_time <= start_time:
            raise ValidationError("End time must be after start time.")
        
        # Don't allow changes if session has attendance records
        if self.instance and self.instance.attendance_records.exists():
            if start_time != self.instance.start_time or end_time != self.instance.end_time:
                raise ValidationError(
                    "Cannot change session times after attendance has been recorded."
                )
        
        return cleaned_data


# ========== ATTENDANCE CHECK-IN FORMS ==========

class QRCheckInForm(forms.Form):
    """
    Form for QR code check-in
    """
    session_code = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Scan QR code or enter session code'
        })
    )
    
    def clean_session_code(self):
        code = self.cleaned_data.get('session_code')
        
        try:
            session = AttendanceSession.objects.get(session_code=code)
            
            # Check if session is active
            if not session.is_active_now():
                raise ValidationError("This session is not currently active.")
            
            return code
        except AttendanceSession.DoesNotExist:
            raise ValidationError("Invalid session code.")


class ManualCheckInForm(forms.Form):
    """
    Form for manual check-in (admin/staff only)
    """
    student_id = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter Student ID'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.session = kwargs.pop('session', None)
        super().__init__(*args, **kwargs)
    
    def clean_student_id(self):
        student_id = self.cleaned_data.get('student_id')
        
        try:
            student = User.objects.get(
                student_id=student_id,
                user_type__in=['student', 'executive']
            )
            
            # Check if already checked in
            if self.session and AttendanceRecord.objects.filter(
                session=self.session,
                user=student
            ).exists():
                raise ValidationError(f"{student.get_full_name()} has already checked in.")
            
            return student_id
        except User.DoesNotExist:
            raise ValidationError("No student found with this ID.")


class BulkCheckInForm(forms.Form):
    """
    Form for bulk check-in via CSV
    """
    file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv,.txt'
        }),
        help_text="Upload CSV file with student IDs (one per line)"
    )
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        
        if file:
            if not file.name.endswith(('.csv', '.txt')):
                raise ValidationError("Please upload a CSV or text file.")
            
            if file.size > 1024 * 1024:  # 1MB limit
                raise ValidationError("File size must be less than 1MB.")
        
        return file


# ========== ATTENDANCE CODE FORMS ==========

class AttendanceCodeForm(forms.ModelForm):
    """
    Form for generating attendance codes
    """
    class Meta:
        model = AttendanceCode
        fields = ('session', 'code_type', 'valid_from', 'valid_until', 'max_uses')
        widgets = {
            'session': forms.Select(attrs={'class': 'form-select'}),
            'code_type': forms.Select(attrs={'class': 'form-select'}),
            'valid_from': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'valid_until': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'max_uses': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'value': 1
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('event', None)
        super().__init__(*args, **kwargs)
        
        if self.event:
            self.fields['session'].queryset = self.event.attendance_sessions.all()
            self.fields['session'].empty_label = "All Sessions (Event-wide code)"
            self.fields['session'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        valid_from = cleaned_data.get('valid_from')
        valid_until = cleaned_data.get('valid_until')
        session = cleaned_data.get('session')
        
        if valid_from and valid_until and valid_until <= valid_from:
            raise ValidationError("Valid until must be after valid from.")
        
        if session and self.event and session.event != self.event:
            raise ValidationError("Selected session does not belong to this event.")
        
        return cleaned_data


# ========== EVENT FEEDBACK FORMS ==========

class EventFeedbackForm(forms.ModelForm):
    """
    Form for submitting event feedback
    """
    class Meta:
        model = EventFeedback
        fields = ('rating', 'comment')
        widgets = {
            'rating': forms.RadioSelect(attrs={
                'class': 'form-check-input',
                'choices': [(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]
            }),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Share your thoughts about the event... (optional)'
            }),
        }
        labels = {
            'rating': 'How would you rate this event?',
            'comment': 'Additional Comments',
        }
    
    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('event', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        
        if self.event and self.user:
            # Check if user attended the event
            try:
                attendee = EventAttendee.objects.get(event=self.event, user=self.user)
                if not attendee.attended:
                    raise ValidationError("Only attendees can submit feedback.")
            except EventAttendee.DoesNotExist:
                raise ValidationError("You must be registered for this event to submit feedback.")
            
            # Check if already submitted feedback
            if EventFeedback.objects.filter(event=self.event, user=self.user).exists():
                raise ValidationError("You have already submitted feedback for this event.")
        
        return cleaned_data


class FeedbackSearchForm(forms.Form):
    """
    Form for searching and filtering feedback (admin/staff only)
    """
    event = forms.ModelChoiceField(
        queryset=Event.objects.all(),
        required=False,
        empty_label="All Events",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    min_rating = forms.ChoiceField(
        choices=[('', 'Any')] + [(i, f'{i}+ Stars') for i in range(1, 6)],
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
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search in comments...'
        })
    )


# ========== ATTENDANCE REPORTS FORMS ==========

class AttendanceReportForm(forms.Form):
    """
    Form for generating attendance reports
    """
    REPORT_TYPES = (
        ('summary', 'Summary Report'),
        ('detailed', 'Detailed Report'),
        ('hourly', 'Hourly Breakdown'),
        ('sessions', 'By Session'),
    )
    
    event = forms.ModelChoiceField(
        queryset=Event.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    report_type = forms.ChoiceField(
        choices=REPORT_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    session = forms.ModelChoiceField(
        queryset=AttendanceSession.objects.all(),
        required=False,
        empty_label="All Sessions",
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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['session'].queryset = AttendanceSession.objects.none()
        
        if 'event' in self.data:
            try:
                event_id = int(self.data.get('event'))
                self.fields['session'].queryset = AttendanceSession.objects.filter(event_id=event_id)
            except (ValueError, TypeError):
                pass


# ========== REMINDER FORMS ==========

class EventReminderForm(forms.Form):
    """
    Form for sending event reminders
    """
    REMINDER_TIMINGS = (
        (1, '1 hour before'),
        (2, '2 hours before'),
        (6, '6 hours before'),
        (12, '12 hours before'),
        (24, '24 hours before'),
        (48, '48 hours before'),
    )
    
    REMINDER_METHODS = (
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('both', 'Both Email and SMS'),
    )
    
    reminder_time = forms.ChoiceField(
        choices=REMINDER_TIMINGS,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    reminder_method = forms.ChoiceField(
        choices=REMINDER_METHODS,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    custom_message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional custom message to include in reminder'
        })
    )
    send_to_all = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


# ========== EXPORT FORMS ==========

class EventExportForm(forms.Form):
    """
    Form for exporting event data
    """
    EXPORT_TYPES = (
        ('attendees', 'Attendee List'),
        ('attendance', 'Attendance Records'),
        ('feedback', 'Feedback Data'),
        ('all', 'All Data'),
    )
    
    export_type = forms.ChoiceField(
        choices=EXPORT_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    include_sessions = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    format = forms.ChoiceField(
        choices=[
            ('csv', 'CSV'),
            ('excel', 'Excel'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True,
        initial='csv'
    )