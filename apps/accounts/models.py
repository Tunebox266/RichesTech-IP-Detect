# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import FileExtensionValidator
import random
import string
import qrcode
from io import BytesIO
from django.core.files import File
from PIL import Image

class User(AbstractUser):
    USER_TYPES = (
        ('student', 'Student'),
        ('executive', 'Student Executive'),
        ('staff', 'Staff'),
        ('admin', 'Admin'),
    )
    
    PROGRAM_TYPES = (
        ('regular', 'Regular'),
        ('weekend', 'Weekend'),
    )
    
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='student')
    student_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    staff_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    program_type = models.CharField(max_length=10, choices=PROGRAM_TYPES, null=True, blank=True)
    year_of_admission = models.IntegerField(null=True, blank=True)
    level = models.IntegerField(choices=[(100, '100'), (200, '200'), (300, '300'), (400, '400')], null=True, blank=True)
    profile_image = models.ImageField(upload_to='profiles/', null=True, blank=True)
    title = models.CharField(max_length=50, blank=True, null=True)  # e.g., Dr., Prof.
    phone_number = models.CharField(max_length=15, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    requires_password_change = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    failed_login_attempts = models.IntegerField(default=0)
    account_locked_until = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return self.get_full_name() or self.username
    
    def generate_student_id(self):
        """Generate student ID in format: BTMLYY0001"""
        prefix = 'BTML'
        year = str(self.year_of_admission)[-2:]
        last_student = User.objects.filter(
            student_id__startswith=f'{prefix}{year}'
        ).order_by('-student_id').first()
        
        if last_student:
            last_number = int(last_student.student_id[-4:])
            new_number = last_number + 1
        else:
            new_number = 1
            
        return f'{prefix}{year}{new_number:04d}'
    
    def save(self, *args, **kwargs):
    # Only generate student_id if user_type requires it AND year_of_admission exists
        if self.user_type in ['student', 'executive'] and not self.student_id:
            if self.year_of_admission:  # Only generate if year_of_admission is set
                self.student_id = self.generate_student_id()
        # If no year_of_admission, leave student_id blank for now
        super().save(*args, **kwargs)
    
    #def save(self, *args, **kwargs):
   #     if self.user_type in ['student', 'executive'] and not self.student_id:
    #        self.student_id = self.generate_student_id()
    #    super().save(*args, **kwargs)


# ========== NEW STUDENT EXECUTIVE MODEL ==========
class StudentExecutive(models.Model):
    """
    Extended model for Student Executives with additional permissions
    and executive-specific information
    """
    EXECUTIVE_POSITIONS = (
        ('president', 'President'),
        ('vice_president', 'Vice President'),
        ('secretary', 'Secretary'),
        ('assistant_secretary', 'Assistant Secretary'),
        ('treasurer', 'Treasurer'),
        ('financial_secretary', 'Financial Secretary'),
        ('public_relations_officer', 'Public Relations Officer'),
        ('welfare_director', 'Welfare Director'),
        ('sports_director', 'Sports Director'),
        ('social_director', 'Social Director'),
        ('academic_director', 'Academic Director'),
        ('technical_director', 'Technical Director'),
        ('project_manager', 'Project Manager'),
        ('class_representative', 'Class Representative'),
    )
    
    EXECUTIVE_LEVELS = (
        ('departmental', 'Departmental Executive'),
        ('faculty', 'Faculty Executive'),
        ('institutional', 'Institutional Executive'),
    )
    
    TENURE_STATUS = (
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('resigned', 'Resigned'),
        ('suspended', 'Suspended'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='account_executive_profile')
    position = models.CharField(max_length=30, choices=EXECUTIVE_POSITIONS)
    executive_level = models.CharField(max_length=20, choices=EXECUTIVE_LEVELS, default='departmental')
    tenure_start_date = models.DateField()
    tenure_end_date = models.DateField()
    tenure_status = models.CharField(max_length=10, choices=TENURE_STATUS, default='active')
    
    # Executive Permissions
    can_manage_events = models.BooleanField(default=True)
    can_upload_materials = models.BooleanField(default=True)
    can_send_announcements = models.BooleanField(default=True)
    can_take_attendance = models.BooleanField(default=True)
    can_manage_complaints = models.BooleanField(default=True)
    can_view_financial_reports = models.BooleanField(default=False)  # Only for treasurer/financial sec
    
    # Additional Executive Info
    manifesto = models.TextField(blank=True, help_text="Executive's manifesto or vision")
    achievements = models.TextField(blank=True, help_text="Achievements during tenure")
    executive_image = models.ImageField(
        upload_to='executives/', 
        null=True, 
        blank=True,
        help_text="Official executive portrait"
    )
    signature = models.ImageField(
        upload_to='signatures/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(['png', 'jpg', 'jpeg'])]
    )
    
    # Contact for executive duties
    official_email = models.EmailField(blank=True, help_text="Official executive email")
    office_location = models.CharField(max_length=100, blank=True)
    office_hours = models.CharField(max_length=200, blank=True)
    
    # Meeting preferences
    prefers_meeting_reminders = models.BooleanField(default=True)
    meeting_reminder_time = models.IntegerField(
        default=60, 
        help_text="Minutes before meeting to send reminder"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-tenure_start_date', 'position']
        verbose_name = "Student Executive"
        verbose_name_plural = "Student Executives"
        unique_together = ['user', 'tenure_start_date']  # Prevent duplicate active tenures
        
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_position_display()}"
    
    @property
    def is_active_executive(self):
        """Check if executive is currently active"""
        from django.utils import timezone
        today = timezone.now().date()
        return (self.tenure_status == 'active' and 
                self.tenure_start_date <= today <= self.tenure_end_date)
    
    @property
    def remaining_tenure_days(self):
        """Calculate remaining days in tenure"""
        from django.utils import timezone
        if self.is_active_executive:
            remaining = (self.tenure_end_date - timezone.now().date()).days
            return max(0, remaining)
        return 0
    
    def generate_executive_id_card(self):
        """Generate digital ID card for executive"""
        # Implementation for ID card generation
        pass
    
    def get_executive_dashboard_stats(self):
        """Get statistics for executive dashboard"""
        from events.models import Event
        from communication.models import Complaint
        
        return {
            'events_organized': Event.objects.filter(organizer=self.user).count(),
            'upcoming_events': Event.objects.filter(
                organizer=self.user, 
                date__gte=timezone.now()
            ).count(),
            'pending_complaints': Complaint.objects.filter(
                assigned_to=self.user,
                status='pending'
            ).count(),
            'total_attendees': Attendance.objects.filter(
                event__organizer=self.user
            ).count()
        }


# ========== EXECUTIVE MEETING MODEL ==========
class ExecutiveMeeting(models.Model):
    """
    Model for executive meetings and discussions
    """
    MEETING_TYPES = (
        ('regular', 'Regular Meeting'),
        ('emergency', 'Emergency Meeting'),
        ('planning', 'Planning Session'),
        ('review', 'Review Meeting'),
        ('general', 'General Assembly'),
    )
    
    MEETING_STATUS = (
        ('scheduled', 'Scheduled'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('postponed', 'Postponed'),
    )
    
    title = models.CharField(max_length=200)
    meeting_type = models.CharField(max_length=20, choices=MEETING_TYPES, default='regular')
    description = models.TextField()
    
    # Meeting Details
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    venue = models.CharField(max_length=200)
    is_virtual = models.BooleanField(default=False)
    meeting_link = models.URLField(blank=True, help_text="Zoom/Google Meet link if virtual")
    
    # Organizer and Participants
    organized_by = models.ForeignKey(
        StudentExecutive, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='organized_meetings'
    )
    participants = models.ManyToManyField(
        StudentExecutive,
        related_name='meetings',
        blank=True
    )
    
    # Meeting Materials
    agenda = models.TextField()
    minutes = models.TextField(blank=True)
    attachments = models.FileField(
        upload_to='meeting_attachments/',
        null=True,
        blank=True
    )
    
    # Status and Tracking
    status = models.CharField(max_length=20, choices=MEETING_STATUS, default='scheduled')
    qr_code = models.ImageField(upload_to='meeting_qrcodes/', null=True, blank=True)
    meeting_code = models.CharField(max_length=10, unique=True, blank=True)
    
    # Attendance
    requires_attendance = models.BooleanField(default=True)
    attendance_recorded = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-start_time']
        
    def __str__(self):
        return f"{self.title} - {self.date}"
    
    def save(self, *args, **kwargs):
        if not self.meeting_code:
            self.meeting_code = self.generate_meeting_code()
        if not self.qr_code:
            self.generate_qr_code()
        super().save(*args, **kwargs)
    
    def generate_meeting_code(self):
        """Generate unique meeting code"""
        import random
        import string
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    def generate_qr_code(self):
        """Generate QR code for meeting check-in"""
        import qrcode
        from io import BytesIO
        from django.core.files import File
        
        qr = qrcode.QRCode(
            version=1,
            box_size=10,
            border=5
        )
        
        meeting_data = f"Meeting: {self.title}\nCode: {self.meeting_code}\nDate: {self.date}\nVenue: {self.venue}"
        qr.add_data(meeting_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        
        filename = f"meeting_{self.meeting_code}_qrcode.png"
        self.qr_code.save(filename, File(buffer), save=False)


# ========== MEETING ATTENDANCE MODEL ==========
class MeetingAttendance(models.Model):
    """
    Track attendance for executive meetings
    """
    meeting = models.ForeignKey(ExecutiveMeeting, on_delete=models.CASCADE, related_name='attendances')
    executive = models.ForeignKey(StudentExecutive, on_delete=models.CASCADE, related_name='meeting_attendances')
    check_in_time = models.DateTimeField(auto_now_add=True)
    check_in_method = models.CharField(
        max_length=20,
        choices=[
            ('qr_code', 'QR Code'),
            ('manual', 'Manual'),
            ('automatic', 'Automatic')
        ],
        default='qr_code'
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_info = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['meeting', 'executive']  # Prevent duplicate check-ins
        
    def __str__(self):
        return f"{self.executive} - {self.meeting}"


# ========== EXECUTIVE TASK MODEL ==========
class ExecutiveTask(models.Model):
    """
    Track tasks assigned to executives
    """
    TASK_PRIORITY = (
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    )
    
    TASK_STATUS = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    assigned_to = models.ForeignKey(
        StudentExecutive, 
        on_delete=models.CASCADE,
        related_name='assigned_tasks'
    )
    assigned_by = models.ForeignKey(
        StudentExecutive,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tasks'
    )
    
    priority = models.CharField(max_length=10, choices=TASK_PRIORITY, default='medium')
    status = models.CharField(max_length=20, choices=TASK_STATUS, default='pending')
    
    due_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    
    related_to_meeting = models.ForeignKey(
        ExecutiveMeeting, 
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    attachments = models.FileField(upload_to='task_attachments/', null=True, blank=True)
    feedback = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-priority', 'due_date']
        
    def __str__(self):
        return self.title
    
    def mark_completed(self):
        """Mark task as completed"""
        from django.utils import timezone
        self.status = 'completed'
        self.completed_date = timezone.now().date()
        self.save()


# ========== EXECUTIVE DISCUSSION FORUM ==========
class ExecutiveDiscussion(models.Model):
    """
    Discussion forum for executives
    """
    meeting = models.ForeignKey(
        ExecutiveMeeting, 
        on_delete=models.CASCADE,
        related_name='discussions',
        null=True,
        blank=True
    )
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_by = models.ForeignKey(StudentExecutive, on_delete=models.CASCADE)
    is_announcement = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    
    attachments = models.FileField(
        upload_to='discussion_attachments/',
        null=True,
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_pinned', '-created_at']
        
    def __str__(self):
        return self.title


class DiscussionComment(models.Model):
    """
    Comments on executive discussions
    """
    discussion = models.ForeignKey(ExecutiveDiscussion, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(StudentExecutive, on_delete=models.CASCADE)
    content = models.TextField()
    attachments = models.FileField(upload_to='comment_attachments/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        
    def __str__(self):
        return f"Comment by {self.author} on {self.discussion}"


# Keep existing ActivityLog and LoginAttempt models
class ActivityLog(models.Model):
    ACTION_TYPES = (
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('password_change', 'Password Change'),
        ('payment', 'Payment'),
        ('course_registration', 'Course Registration'),
        ('file_upload', 'File Upload'),
        ('admin_action', 'Admin Action'),
        ('executive_action', 'Executive Action'),  # Added new action type
        ('meeting_created', 'Meeting Created'),    # Added new action type
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()
    details = models.JSONField(default=dict)
    
    class Meta:
        ordering = ['-timestamp']


class LoginAttempt(models.Model):
    username = models.CharField(max_length=150)
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(auto_now_add=True)
    successful = models.BooleanField(default=False)


# apps/accounts/models.py - Add this model

class TaskComment(models.Model):
    """Comments on executive tasks"""
    task = models.ForeignKey(ExecutiveTask, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(StudentExecutive, on_delete=models.CASCADE, related_name='task_comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Comment by {self.author.user.get_full_name()} on {self.task.title}"

