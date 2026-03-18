# directory/models.py
from django.db import models
from django.contrib.auth import get_user_model
import qrcode
from io import BytesIO
from django.core.files import File
from PIL import Image
from datetime import date
from apps.core.models import AcademicSetting
import os

User = get_user_model()


class StudentIDCard(models.Model):
    student = models.OneToOneField(User, on_delete=models.CASCADE, related_name='id_card')
    card_number = models.CharField(max_length=20, unique=True)
    
    # Front of card fields
    blood_group = models.CharField(max_length=5, blank=True, null=True, 
                                   choices=[
                                       ('A+', 'A+'), ('A-', 'A-'),
                                       ('B+', 'B+'), ('B-', 'B-'),
                                       ('AB+', 'AB+'), ('AB-', 'AB-'),
                                       ('O+', 'O+'), ('O-', 'O-')
                                   ])
    qr_code = models.ImageField(upload_to='id_qrcodes/', null=True, blank=True)
    valid_until = models.DateField(default=date(2025, 12, 31))
    issued_at = models.DateTimeField(auto_now_add=True)
    
    # Student Signature - NEW FIELD
    student_signature = models.ImageField(
        upload_to='signatures/', 
        null=True, 
        blank=True,
        help_text="Upload student's signature (PNG with transparent background recommended)"
    )
    
    # Emergency contact (back of card)
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)
    emergency_relationship = models.CharField(max_length=50, blank=True, null=True)
    emergency_phone = models.CharField(max_length=20, blank=True, null=True)
    emergency_address = models.TextField(blank=True, null=True)
    
    # Medical information
    allergies = models.TextField(blank=True, null=True, help_text="Any known allergies")
    medical_conditions = models.TextField(blank=True, null=True, help_text="Important medical conditions")
    
    # Tracking
    last_downloaded = models.DateTimeField(null=True, blank=True)
    download_count = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "Student ID Card"
        verbose_name_plural = "Student ID Cards"
    
    def __str__(self):
        return f"ID Card - {self.student.get_full_name()} ({self.card_number})"
    
    def generate_qr_code(self):
        """Generate QR code with student information"""
        qr = qrcode.QRCode(
            version=1,
            box_size=10,
            border=5
        )
        qr_data = f"""MELTSA-TaTU STUDENT ID
    Name: {self.student.get_full_name()}
    Student ID: {self.student.student_id}
    Level: {self.student.level}
    Program: {self.student.get_program_type_display()}
    Blood Group: {self.blood_group or 'N/A'}
    Card No: {self.card_number}
    Valid Until: {self.valid_until}"""
        
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        
        filename = f"qr_{self.student.student_id}.png"
        self.qr_code.save(filename, File(buffer), save=False)
    
    def save(self, *args, **kwargs):
        if not self.qr_code:
            self.generate_qr_code()
        super().save(*args, **kwargs)
    
    def increment_download_count(self):
        """Increment download count"""
        self.download_count += 1
        self.last_downloaded = timezone.now()
        self.save(update_fields=['download_count', 'last_downloaded'])




class PastQuestion(models.Model):
    """Past examination questions"""
    LEVEL_CHOICES = (
        (100, 'Level 100'),
        (200, 'Level 200'),
        (300, 'Level 300'),
        (400, 'Level 400'),
    )
    
    SEMESTER_CHOICES = (
        (1, 'First Semester'),
        (2, 'Second Semester'),
    )
    
    title = models.CharField(max_length=200)
    course_code = models.CharField(max_length=20, help_text="e.g., BTML201")
    course_name = models.CharField(max_length=200, blank=True)
    level = models.IntegerField(choices=LEVEL_CHOICES)
    semester = models.IntegerField(choices=SEMESTER_CHOICES)
    academic_year = models.CharField(max_length=20, help_text="e.g., 2024/2025")
    exam_year = models.IntegerField(help_text="Year the exam was taken")
    
    # File upload
    file = models.FileField(upload_to='past_questions/')
    file_size = models.IntegerField(default=0, editable=False)
    
    # Metadata
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='uploaded_past_questions')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Statistics
    downloads = models.IntegerField(default=0)
    views = models.IntegerField(default=0)
    
    # Status
    is_approved = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-exam_year', 'level', 'course_code']
        verbose_name = "Past Question"
        verbose_name_plural = "Past Questions"
    
    def __str__(self):
        return f"{self.course_code} - {self.exam_year} ({self.get_level_display()})"
    
    def save(self, *args, **kwargs):
        if self.file and not self.file_size:
            self.file_size = self.file.size
        super().save(*args, **kwargs)
    
    def filename(self):
        return os.path.basename(self.file.name)


class StudentHandbook(models.Model):
    """Student handbook / manual"""
    title = models.CharField(max_length=200)
    version = models.CharField(max_length=20, help_text="e.g., 2024 Edition")
    description = models.TextField(blank=True)
    
    # File upload
    file = models.FileField(upload_to='handbooks/')
    cover_image = models.ImageField(upload_to='handbook_covers/', null=True, blank=True)
    file_size = models.IntegerField(default=0, editable=False)
    
    # Metadata
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='uploaded_handbooks')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Statistics
    downloads = models.IntegerField(default=0)
    views = models.IntegerField(default=0)
    
    # Validity
    is_current = models.BooleanField(default=True, help_text="Is this the current handbook?")
    effective_date = models.DateField(help_text="Date from which this handbook is effective")
    
    class Meta:
        ordering = ['-effective_date']
        verbose_name = "Student Handbook"
        verbose_name_plural = "Student Handbooks"
    
    def __str__(self):
        return f"{self.title} - {self.version}"
    
    def save(self, *args, **kwargs):
        if self.file and not self.file_size:
            self.file_size = self.file.size
        super().save(*args, **kwargs)
        
        # If this is set as current, unset others
        if self.is_current:
            StudentHandbook.objects.exclude(pk=self.pk).update(is_current=False)


class AcademicCalendar(models.Model):
    """Academic calendar events"""
    EVENT_TYPES = (
        ('academic', 'Academic'),
        ('registration', 'Registration'),
        ('examination', 'Examination'),
        ('holiday', 'Holiday'),
        ('event', 'Event'),
        ('deadline', 'Deadline'),
    )
    
    title = models.CharField(max_length=200)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, default='academic')
    description = models.TextField(blank=True)
    
    # Date range
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_all_day = models.BooleanField(default=True)
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    
    # Academic context
    academic_year = models.CharField(max_length=20, help_text="e.g., 2024/2025")
    semester = models.IntegerField(choices=[(1, 'First Semester'), (2, 'Second Semester')], null=True, blank=True)
    level = models.IntegerField(choices=[(100, 'All Levels'), (200, 'Level 200'), (300, 'Level 300'), (400, 'Level 400')], default=100)
    
    # Location
    venue = models.CharField(max_length=200, blank=True, help_text="Location if applicable")
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_calendar_events')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_important = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['start_date', 'start_time']
        verbose_name = "Academic Calendar Event"
        verbose_name_plural = "Academic Calendar Events"
    
    def __str__(self):
        return f"{self.title} - {self.start_date}"
    
    @property
    def is_past(self):
        from django.utils import timezone
        return self.end_date < timezone.now().date() if self.end_date else self.start_date < timezone.now().date()
    
    @property
    def is_ongoing(self):
        from django.utils import timezone
        today = timezone.now().date()
        if self.end_date:
            return self.start_date <= today <= self.end_date
        return self.start_date == today