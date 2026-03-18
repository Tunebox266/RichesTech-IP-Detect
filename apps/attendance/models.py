# attendance/models.py
from django.db import models
from django.contrib.auth import get_user_model
from apps.events.models import Event

User = get_user_model()

class AttendanceSession(models.Model):
    SESSION_TYPES = (
        ('meeting', 'Meeting'),
        ('seminar', 'Seminar'),
        ('event', 'Event'),
    )
    
    title = models.CharField(max_length=200)
    session_type = models.CharField(max_length=10, choices=SESSION_TYPES)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=True, blank=True, related_name='attendance_sessions')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    venue = models.CharField(max_length=200)
    qr_code = models.ImageField(upload_to='qr_codes/', null=True, blank=True)
    qr_secret = models.CharField(max_length=100, unique=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_sessions')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.title} - {self.date}"
    
    def get_attendance_count(self):
        return self.attendance_records.count()

class AttendanceRecord(models.Model):
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name='attendance_records')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendance_records_attendance')
    checked_in_at = models.DateTimeField(auto_now_add=True)
    checked_in_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='marked_attendance')
    method = models.CharField(max_length=20, choices=(
        ('qr', 'QR Code'),
        ('manual', 'Manual'),
        ('id_input', 'ID Input'),
    ))
    
    class Meta:
        unique_together = ['session', 'student']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.session.title}"