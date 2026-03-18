# payments/models.py
from django.db import models
from django.contrib.auth import get_user_model
from apps.core.models import AcademicSetting
from django.utils import timezone
import uuid

User = get_user_model()

class Due(models.Model):
    DUE_TYPES = (
        ('academic', 'Academic Due'),
        ('association', 'Association Due'),
        ('other', 'Other'),
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_type = models.CharField(max_length=20, choices=DUE_TYPES, default='association')
    academic_setting = models.ForeignKey(AcademicSetting, on_delete=models.CASCADE)
    deadline = models.DateField()
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_dues')
    created_at = models.DateTimeField(auto_now_add=True)
    target_levels = models.JSONField(default=list)  # [100, 200, 300, 400]
    
    def __str__(self):
        return f"{self.title} - GHS {self.amount}"
    
    def get_total_paid(self):
        return self.payments.filter(status='success').aggregate(total=models.Sum('amount'))['total'] or 0
    
    def get_total_students(self):
        return User.objects.filter(
            user_type='student',
            level__in=self.target_levels
        ).count()
    
    def get_paid_students(self):
        return self.payments.filter(
            status='success',
            student__level__in=self.target_levels
        ).values('student').distinct().count()

class Payment(models.Model):
    PAYMENT_STATUS = (
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    )
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    due = models.ForeignKey(Due, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    status = models.CharField(max_length=10, choices=PAYMENT_STATUS, default='pending')
    paystack_reference = models.CharField(max_length=100, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.reference}"
    
    def save(self, *args, **kwargs):
        if self.status == 'success' and not self.paid_at:
            self.paid_at = timezone.now()
        super().save(*args, **kwargs)

class PaymentHistory(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='history')
    status = models.CharField(max_length=10, choices=Payment.PAYMENT_STATUS)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']