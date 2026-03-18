# complaints/models.py
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Complaint(models.Model):
    COMPLAINT_TYPES = (
        ('academic', 'Academic'),
        ('lecturer', 'Lecturer Concern'),
        ('association', 'Association Issue'),
        ('facility', 'Facility'),
        ('other', 'Other'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('resolved', 'Resolved'),
        ('rejected', 'Rejected'),
    )
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='student_complaints')
    complaint_type = models.CharField(max_length=15, choices=COMPLAINT_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    attachment = models.FileField(upload_to='complaints/', null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.title}"

class ComplaintResponse(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='responses')
    responder = models.ForeignKey(User, on_delete=models.CASCADE, related_name='complaint_responses')
    message = models.TextField()
    attachment = models.FileField(upload_to='complaint_responses/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Response to {self.complaint.title}"