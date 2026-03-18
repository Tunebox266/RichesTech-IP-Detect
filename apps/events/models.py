# events/models.py
from django.db import models
from django.contrib.auth import get_user_model
import qrcode
from io import BytesIO
from django.core.files import File
import uuid

User = get_user_model()


class Event(models.Model):
    EVENT_TYPES = (
        ('orientation', 'Orientation'),
        ('health_screening', 'Health Screening'),
        ('general_meeting', 'General Meeting'),
        ('seminar', 'Seminar'),
        ('social', 'Social Event'),
        ('other', 'Other'),
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    venue = models.CharField(max_length=200)
    poster = models.ImageField(upload_to='event_posters/', null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_events')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    max_attendees = models.IntegerField(null=True, blank=True)
    requires_attendance_tracking = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-start_date']
    
    def __str__(self):
        return self.title
    
    def get_attendee_count(self):
        return self.attendees.count()
    
    def get_registered_count(self):
        return self.attendees.filter(attended=False).count()
    
    def get_checked_in_count(self):
        return self.attendees.filter(attended=True).count()
    
    def is_full(self):
        if self.max_attendees:
            return self.get_attendee_count() >= self.max_attendees
        return False


class EventAttendee(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='attendees')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='events_attending')
    registered_at = models.DateTimeField(auto_now_add=True)
    attended = models.BooleanField(default=False)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    check_in_method = models.CharField(
        max_length=20,
        choices=[
            ('qr_code', 'QR Code'),
            ('manual', 'Manual'),
            ('automatic', 'Automatic'),
        ],
        default='manual'
    )
    
    class Meta:
        unique_together = ['event', 'user']
        ordering = ['-registered_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.event.title}"
    
    def check_in(self, method='manual'):
        """Mark attendee as checked in"""
        from django.utils import timezone
        self.attended = True
        self.checked_in_at = timezone.now()
        self.check_in_method = method
        self.save()


class AttendanceSession(models.Model):
    """
    Model for attendance sessions (for events that span multiple days or have multiple sessions)
    """
    SESSION_TYPES = (
        ('day1', 'Day 1'),
        ('day2', 'Day 2'),
        ('day3', 'Day 3'),
        ('morning', 'Morning Session'),
        ('afternoon', 'Afternoon Session'),
        ('evening', 'Evening Session'),
        ('workshop', 'Workshop'),
        ('other', 'Other'),
    )
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='attendance_sessions_events')
    name = models.CharField(max_length=100)
    session_type = models.CharField(max_length=20, choices=SESSION_TYPES, default='other')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    venue = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    
    # QR Code for check-in
    qr_code = models.ImageField(upload_to='attendance_qrcodes/', null=True, blank=True)
    session_code = models.CharField(max_length=20, unique=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['start_time']
    
    def __str__(self):
        return f"{self.event.title} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.session_code:
            self.session_code = self.generate_session_code()
        if not self.qr_code:
            self.generate_qr_code()
        super().save(*args, **kwargs)
    
    def generate_session_code(self):
        """Generate unique session code"""
        import random
        import string
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    def generate_qr_code(self):
        """Generate QR code for session check-in"""
        import qrcode
        from io import BytesIO
        from django.core.files import File
        
        qr = qrcode.QRCode(
            version=1,
            box_size=10,
            border=5
        )
        
        session_data = f"Session: {self.name}\nCode: {self.session_code}\nEvent: {self.event.title}\nTime: {self.start_time.strftime('%Y-%m-%d %H:%M')}"
        qr.add_data(session_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        
        filename = f"session_{self.session_code}_qrcode.png"
        self.qr_code.save(filename, File(buffer), save=False)
    
    def get_checked_in_count(self):
        return self.attendance_records.count()
    
    def is_active_now(self):
        """Check if session is currently active"""
        from django.utils import timezone
        now = timezone.now()
        return self.start_time <= now <= self.end_time


class AttendanceRecord(models.Model):
    """
    Individual attendance records for sessions
    """
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name='attendance_records')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendance_records_events')
    checked_in_at = models.DateTimeField(auto_now_add=True)
    check_in_method = models.CharField(
        max_length=20,
        choices=[
            ('qr_code', 'QR Code'),
            ('manual', 'Manual'),
            ('automatic', 'Automatic'),
        ],
        default='qr_code'
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_info = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['session', 'user']  # Prevent duplicate check-ins
        ordering = ['-checked_in_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.session}"


class AttendanceCode(models.Model):
    """
    Model for generating temporary attendance codes
    """
    CODE_TYPES = (
        ('qr', 'QR Code'),
        ('numeric', 'Numeric Code'),
        ('alphanumeric', 'Alphanumeric'),
    )
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='event_attendance_codes')
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name='attendance_codes', null=True, blank=True)
    code = models.CharField(max_length=50, unique=True)
    code_type = models.CharField(max_length=20, choices=CODE_TYPES, default='qr')
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    max_uses = models.IntegerField(default=1)
    current_uses = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_codes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.code} - {self.event.title}"
    
    def is_valid(self):
        """Check if code is still valid"""
        from django.utils import timezone
        now = timezone.now()
        return (self.is_active and 
                self.valid_from <= now <= self.valid_until and 
                self.current_uses < self.max_uses)
    
    def use_code(self):
        """Increment usage count"""
        if self.is_valid():
            self.current_uses += 1
            self.save()
            return True
        return False


class EventFeedback(models.Model):
    """
    Model for collecting feedback from event attendees
    """
    RATING_CHOICES = [(i, i) for i in range(1, 6)]
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='feedback')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_feedback')
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['event', 'user']  # One feedback per user per event
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.event.title} - {self.rating}/5"


class EventReminder(models.Model):
    """
    Model for scheduling event reminders
    """
    REMINDER_TYPES = (
        ('email', 'Email'),
        ('push', 'Push Notification'),
        ('sms', 'SMS'),
    )
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='reminders')
    reminder_type = models.CharField(max_length=10, choices=REMINDER_TYPES)
    remind_at = models.DateTimeField()
    sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['remind_at']
    
    def __str__(self):
        return f"{self.event.title} - {self.reminder_type} - {self.remind_at}"
