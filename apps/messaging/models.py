# messaging/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import os

User = get_user_model()


class Message(models.Model):
    """
    Model for individual messages between users
    """
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages', null=True, blank=True)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    parent_message = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    is_broadcast = models.BooleanField(default=False)
    broadcast_groups = models.JSONField(default=list)  # ['students', 'staff', 'executives']
    is_urgent = models.BooleanField(default=False)
    is_replied = models.BooleanField(default=False)
    is_starred = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    is_draft = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['sender', 'sent_at']),
            models.Index(fields=['recipient', 'sent_at']),
            models.Index(fields=['is_broadcast']),
            models.Index(fields=['is_archived']),
            models.Index(fields=['is_draft']),
        ]
    
    def __str__(self):
        return f"{self.sender.get_full_name()} - {self.subject[:50]}"
    
    def mark_as_read(self):
        if not self.read_at:
            self.read_at = timezone.now()
            self.save()
    
    def get_conversation(self):
        """Get all messages in this conversation thread"""
        if self.parent_message:
            return self.parent_message.get_conversation()
        return Message.objects.filter(
            models.Q(parent_message=self) | models.Q(pk=self.pk)
        ).order_by('sent_at')


class MessageAttachment(models.Model):
    """
    Model for file attachments on messages
    """
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='message_attachments/')
    filename = models.CharField(max_length=255)
    file_size = models.IntegerField(default=0)  # Size in bytes
    content_type = models.CharField(max_length=100, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['uploaded_at']
    
    def __str__(self):
        return self.filename
    
    def save(self, *args, **kwargs):
        if self.file and not self.filename:
            self.filename = os.path.basename(self.file.name)
        if self.file and not self.file_size:
            self.file_size = self.file.size
        super().save(*args, **kwargs)


class Conversation(models.Model):
    """
    Model representing a conversation thread between users
    """
    participants = models.ManyToManyField(User, related_name='conversations')
    subject = models.CharField(max_length=200, blank=True)
    last_message_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-last_message_at']
    
    def __str__(self):
        participants_list = list(self.participants.all()[:3])
        names = [p.get_full_name() or p.username for p in participants_list]
        if self.participants.count() > 3:
            names.append('...')
        return f"Conversation: {', '.join(names)}"
    
    def get_last_message(self):
        """Get the most recent message in this conversation"""
        return self.messages.order_by('-sent_at').first()
    
    def get_unread_count(self, user):
        """Get count of unread messages for a user in this conversation"""
        return self.messages.filter(
            ~models.Q(sender=user),
            read_at__isnull=True
        ).count()
    
    def mark_as_read(self, user):
        """Mark all messages in conversation as read for a user"""
        self.messages.filter(
            ~models.Q(sender=user),
            read_at__isnull=True
        ).update(read_at=timezone.now())


class ConversationMessage(models.Model):
    """
    Messages within a conversation
    """
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversation_messages')
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['sent_at']
    
    def __str__(self):
        return f"{self.sender.get_full_name()} - {self.sent_at}"
    
    def mark_as_read(self):
        if not self.read_at:
            self.read_at = timezone.now()
            self.save()


class Broadcast(models.Model):
    """
    Model for broadcast messages (announcements to multiple recipients)
    """
    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )
    
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_broadcasts')
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    requires_acknowledgment = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Recipients (can be individuals or groups)
    recipients = models.ManyToManyField(User, related_name='received_broadcasts', blank=True)
    recipient_groups = models.JSONField(default=list)  # ['all_students', 'all_staff', 'level_100', etc.]
    
    # Tracking
    view_count = models.IntegerField(default=0)
    acknowledgment_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_by', 'created_at']),
            models.Index(fields=['scheduled_for']),
        ]
    
    def __str__(self):
        return self.title
    
    def send(self):
        """Mark broadcast as sent"""
        self.sent_at = timezone.now()
        self.save()
    
    def get_recipient_count(self):
        """Get total number of recipients"""
        return self.recipients.count()
    
    def get_acknowledgment_rate(self):
        """Get percentage of recipients who acknowledged"""
        if self.get_recipient_count() > 0:
            return (self.acknowledgment_count / self.get_recipient_count()) * 100
        return 0


class BroadcastAcknowledgment(models.Model):
    """
    Track acknowledgments for broadcasts
    """
    broadcast = models.ForeignKey(Broadcast, on_delete=models.CASCADE, related_name='acknowledgments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='broadcast_acknowledgments')
    acknowledged_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        unique_together = ['broadcast', 'user']
        ordering = ['-acknowledged_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} acknowledged {self.broadcast.title}"


class Notification(models.Model):
    """
    Model for in-app notifications
    """
    NOTIFICATION_TYPES = (
        ('message', 'New Message'),
        ('broadcast', 'Broadcast'),
        ('reply', 'Message Reply'),
        ('event', 'Event Reminder'),
        ('payment', 'Payment Confirmation'),
        ('due', 'Due Reminder'),
        ('system', 'System Notification'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    content = models.TextField()
    
    # Link to related object (optional)
    related_message = models.ForeignKey(Message, on_delete=models.CASCADE, null=True, blank=True, related_name='message_notifications')
    related_broadcast = models.ForeignKey(Broadcast, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    
    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Delivery
    email_sent = models.BooleanField(default=False)
    push_sent = models.BooleanField(default=False)
    sms_sent = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.title}"
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()
    
    def mark_as_unread(self):
        self.is_read = False
        self.read_at = None
        self.save()


class NotificationPreference(models.Model):
    """
    User preferences for notifications
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Notification channels
    email_messages = models.BooleanField(default=True)
    email_broadcasts = models.BooleanField(default=True)
    email_events = models.BooleanField(default=True)
    email_payments = models.BooleanField(default=True)
    
    in_app_messages = models.BooleanField(default=True)
    in_app_broadcasts = models.BooleanField(default=True)
    in_app_events = models.BooleanField(default=True)
    in_app_payments = models.BooleanField(default=True)
    
    # Digest settings
    email_digest = models.CharField(
        max_length=10,
        choices=[
            ('never', 'Never'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
        ],
        default='never'
    )
    
    # Quiet hours
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Notification preferences for {self.user.get_full_name()}"
    
    def should_send_notification(self, notification_type, channel):
        """Check if notification should be sent based on preferences"""
        pref_map = {
            ('message', 'email'): self.email_messages,
            ('broadcast', 'email'): self.email_broadcasts,
            ('event', 'email'): self.email_events,
            ('payment', 'email'): self.email_payments,
            ('message', 'in_app'): self.in_app_messages,
            ('broadcast', 'in_app'): self.in_app_broadcasts,
            ('event', 'in_app'): self.in_app_events,
            ('payment', 'in_app'): self.in_app_payments,
        }
        
        key = (notification_type, channel)
        return pref_map.get(key, True)  # Default to True if not specified


class Complaint(models.Model):
    """
    Model for complaints and suggestions
    """
    COMPLAINT_TYPES = (
        ('academic', 'Academic Complaint'),
        ('lecturer', 'Lecturer Concern'),
        ('association', 'Association Issue'),
        ('facility', 'Facility Issue'),
        ('suggestion', 'Suggestion'),
        ('other', 'Other'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('resolved', 'Resolved'),
        ('rejected', 'Rejected'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_complaints')
    complaint_type = models.CharField(max_length=20, choices=COMPLAINT_TYPES)
    subject = models.CharField(max_length=200)
    description = models.TextField()
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    assigned_to = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_complaints'
    )
    
    # Anonymous flag
    is_anonymous = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['complaint_type']),
        ]
    
    def __str__(self):
        if self.is_anonymous:
            return f"Anonymous - {self.subject[:50]}"
        return f"{self.user.get_full_name()} - {self.subject[:50]}"
    
    def resolve(self):
        """Mark complaint as resolved"""
        self.status = 'resolved'
        self.resolved_at = timezone.now()
        self.save()


class ComplaintAttachment(models.Model):
    """
    Attachments for complaints
    """
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='complaint_attachments/')
    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.filename


class ComplaintResponse(models.Model):
    """
    Responses to complaints
    """
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='responses')
    responder = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_responses')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Response to {self.complaint.subject[:30]}"