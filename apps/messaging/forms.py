# messaging/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q
import os

from .models import (
    Message, MessageAttachment, Conversation, ConversationMessage,
    Broadcast, BroadcastAcknowledgment, Notification, NotificationPreference,
    Complaint, ComplaintAttachment, ComplaintResponse
)
from apps.accounts.models import User


# ========== CUSTOM WIDGETS ==========

class MultipleFileInput(forms.ClearableFileInput):
    """
    Custom widget that allows multiple file uploads
    """
    allow_multiple_selected = True
    
    def __init__(self, attrs=None):
        if attrs is None:
            attrs = {}
        attrs.update({'multiple': True})
        super().__init__(attrs)


class MultipleFileField(forms.FileField):
    """
    Custom field that handles multiple file uploads
    """
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)]
        return result


# ========== MESSAGE FORMS ==========

class MessageForm(forms.ModelForm):
    """
    Form for sending messages
    """
    attachments = MultipleFileField(
        required=False,
        label='Attachments',
        help_text='You can select multiple files (max 10MB each)'
    )
    
    class Meta:
        model = Message
        fields = ('recipient', 'subject', 'body', 'is_urgent')  # Changed from 'content' to 'body'
        widgets = {
            'recipient': forms.Select(attrs={
                'class': 'form-select',
                'id': 'recipient-select'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter message subject'
            }),
            'body': forms.Textarea(attrs={  # Changed from 'content' to 'body'
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Write your message here...'
            }),
            'is_urgent': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.sender = kwargs.pop('sender', None)
        super().__init__(*args, **kwargs)
        
        # Customize recipient queryset based on sender's permissions
        if self.sender:
            if self.sender.user_type == 'admin':
                # Admin can message everyone
                self.fields['recipient'].queryset = User.objects.filter(is_active=True)
            elif self.sender.user_type == 'staff':
                # Staff can message students and executives
                self.fields['recipient'].queryset = User.objects.filter(
                    Q(user_type__in=['student', 'executive']) | Q(pk=self.sender.pk),
                    is_active=True
                )
            elif self.sender.user_type == 'executive':
                # Executives can message students and other executives
                self.fields['recipient'].queryset = User.objects.filter(
                    Q(user_type__in=['student', 'executive']) | Q(pk=self.sender.pk),
                    is_active=True
                )
            else:
                # Students can only message executives and staff
                self.fields['recipient'].queryset = User.objects.filter(
                    Q(user_type__in=['executive', 'staff']) | Q(pk=self.sender.pk),
                    is_active=True
                )
            
            # Add a placeholder for search functionality (will be handled by JS)
            self.fields['recipient'].widget.attrs.update({
                'data-placeholder': 'Search for recipient...'
            })
    
    def clean_attachments(self):
        """Validate attachments"""
        attachments = self.cleaned_data.get('attachments')
        
        if attachments:
            for file in attachments:
                # Check file size (max 10MB)
                if file.size > 10 * 1024 * 1024:
                    raise ValidationError(f"File {file.name} exceeds 10MB limit.")
                
                # Check file extension (optional)
                ext = os.path.splitext(file.name)[1].lower()
                allowed_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.txt', '.xls', '.xlsx']
                if ext not in allowed_extensions:
                    raise ValidationError(
                        f"File type {ext} not allowed. Allowed types: {', '.join(allowed_extensions)}"
                    )
        
        return attachments
    
    def save(self, commit=True):
        message = super().save(commit=False)
        message.sender = self.sender
        
        if commit:
            message.save()
            
            # Handle attachments
            attachments = self.cleaned_data.get('attachments')
            if attachments:
                for file in attachments:
                    MessageAttachment.objects.create(
                        message=message,
                        file=file,
                        filename=file.name,
                        file_size=file.size,
                        content_type=file.content_type
                    )
        
        return message


class ReplyMessageForm(forms.ModelForm):
    """
    Form for replying to messages
    """
    attachments = MultipleFileField(
        required=False,
        label='Attachments',
        help_text='You can select multiple files (max 10MB each)'
    )
    
    class Meta:
        model = Message
        fields = ('body',)  # Changed from 'content' to 'body'
        widgets = {
            'body': forms.Textarea(attrs={  # Changed from 'content' to 'body'
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Write your reply...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.sender = kwargs.pop('sender', None)
        self.parent_message = kwargs.pop('parent_message', None)
        super().__init__(*args, **kwargs)
    
    def clean_attachments(self):
        """Validate attachments"""
        attachments = self.cleaned_data.get('attachments')
        
        if attachments:
            for file in attachments:
                # Check file size (max 10MB)
                if file.size > 10 * 1024 * 1024:
                    raise ValidationError(f"File {file.name} exceeds 10MB limit.")
        
        return attachments
    
    def save(self, commit=True):
        message = super().save(commit=False)
        message.sender = self.sender
        message.recipient = self.parent_message.sender
        message.subject = f"Re: {self.parent_message.subject}"
        message.parent_message = self.parent_message  # Changed from 'parent' to 'parent_message'
        
        if commit:
            message.save()
            
            # Handle attachments
            attachments = self.cleaned_data.get('attachments')
            if attachments:
                for file in attachments:
                    MessageAttachment.objects.create(
                        message=message,
                        file=file,
                        filename=file.name,
                        file_size=file.size,
                        content_type=file.content_type
                    )
            
            # Mark parent as replied
            self.parent_message.is_replied = True
            self.parent_message.save()
        
        return message


class DraftMessageForm(forms.ModelForm):
    """
    Form for saving message drafts
    """
    class Meta:
        model = Message
        fields = ('recipient', 'subject', 'body')  # Changed from 'content' to 'body'
        widgets = {
            'recipient': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'body': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),  # Changed from 'content' to 'body'
        }


# ========== CONVERSATION FORMS ==========

class ConversationMessageForm(forms.ModelForm):
    """
    Form for sending messages in a conversation
    """
    attachments = MultipleFileField(
        required=False,
        label='Attachments'
    )
    
    class Meta:
        model = ConversationMessage
        fields = ('content',)
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Type your message...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.sender = kwargs.pop('sender', None)
        self.conversation = kwargs.pop('conversation', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        message = super().save(commit=False)
        message.sender = self.sender
        message.conversation = self.conversation
        
        if commit:
            message.save()
            
            # Update conversation's last_message_at
            self.conversation.last_message_at = timezone.now()
            self.conversation.save()
        
        return message


class ConversationCreateForm(forms.Form):
    """
    Form for creating a new conversation
    """
    participants = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'size': 10
        }),
        required=True,
        help_text="Select at least one participant"
    )
    subject = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Conversation subject (optional)'
        })
    )
    initial_message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Write your first message...'
        }),
        required=True
    )
    
    def __init__(self, *args, **kwargs):
        self.creator = kwargs.pop('creator', None)
        super().__init__(*args, **kwargs)
        
        # Filter participants based on creator's permissions
        if self.creator:
            if self.creator.user_type == 'admin':
                self.fields['participants'].queryset = User.objects.filter(is_active=True)
            elif self.creator.user_type == 'staff':
                self.fields['participants'].queryset = User.objects.filter(
                    Q(user_type__in=['student', 'executive']) | Q(pk=self.creator.pk),
                    is_active=True
                )
            else:
                self.fields['participants'].queryset = User.objects.filter(
                    Q(user_type__in=['executive', 'staff']) | Q(pk=self.creator.pk),
                    is_active=True
                )
    
    def clean(self):
        cleaned_data = super().clean()
        participants = cleaned_data.get('participants')
        
        if participants and self.creator:
            # Add creator to participants if not already included
            if self.creator not in participants:
                all_participants = list(participants) + [self.creator]
            else:
                all_participants = participants
            
            # Check if conversation already exists with these participants
            existing = Conversation.objects.filter(
                participants__in=all_participants
            ).distinct()
            
            for conv in existing:
                if set(conv.participants.all()) == set(all_participants):
                    raise ValidationError("A conversation with these participants already exists.")
        
        return cleaned_data


# ========== BROADCAST FORMS ==========

class BroadcastForm(forms.ModelForm):
    """
    Form for creating broadcasts (for executives and staff)
    """
    RECIPIENT_TYPES = (
        ('all_students', 'All Students'),
        ('all_executives', 'All Executives'),
        ('all_staff', 'All Staff'),
        ('by_level', 'Students by Level'),
        ('by_program', 'Students by Program'),
        ('custom', 'Custom Selection'),
    )
    
    recipient_type = forms.ChoiceField(
        choices=RECIPIENT_TYPES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'recipient-type'
        }),
        required=True
    )
    
    target_levels = forms.MultipleChoiceField(
        choices=User._meta.get_field('level').choices,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label="Target Levels"
    )
    
    target_program = forms.ChoiceField(
        choices=[('', 'All Programs')] + list(User.PROGRAM_TYPES),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
        label="Target Program"
    )
    
    custom_recipients = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'size': 10,
            'id': 'custom-recipients'
        }),
        required=False,
        label="Select Recipients"
    )
    
    attachments = MultipleFileField(
        required=False,
        label='Attachments',
        help_text='You can select multiple files (max 10MB each)'
    )
    
    schedule_for = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        }),
        label="Schedule Broadcast (optional)"
    )
    
    class Meta:
        model = Broadcast
        fields = ('title', 'content', 'priority', 'requires_acknowledgment')
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Broadcast title'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': 'Broadcast content...'
            }),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'requires_acknowledgment': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.sender = kwargs.pop('sender', None)
        super().__init__(*args, **kwargs)
        
        # Limit custom recipients based on sender type
        if self.sender:
            if self.sender.user_type == 'staff':
                self.fields['custom_recipients'].queryset = User.objects.filter(
                    Q(user_type__in=['student', 'executive']) | Q(pk=self.sender.pk),
                    is_active=True
                )
            elif self.sender.user_type == 'executive':
                self.fields['custom_recipients'].queryset = User.objects.filter(
                    Q(user_type='student') | Q(pk=self.sender.pk),
                    is_active=True
                )
    
    def clean(self):
        cleaned_data = super().clean()
        recipient_type = cleaned_data.get('recipient_type')
        target_levels = cleaned_data.get('target_levels')
        target_program = cleaned_data.get('target_program')
        custom_recipients = cleaned_data.get('custom_recipients')
        schedule_for = cleaned_data.get('schedule_for')
        
        # Validate based on recipient type
        if recipient_type == 'by_level' and not target_levels:
            raise ValidationError("Please select at least one level.")
        
        if recipient_type == 'by_program' and not target_program:
            raise ValidationError("Please select a program.")
        
        if recipient_type == 'custom' and not custom_recipients:
            raise ValidationError("Please select at least one recipient.")
        
        # Validate schedule time
        if schedule_for and schedule_for < timezone.now():
            raise ValidationError("Schedule time cannot be in the past.")
        
        return cleaned_data
    
    def save(self, commit=True):
        broadcast = super().save(commit=False)
        broadcast.created_by = self.sender
        
        if commit:
            broadcast.save()
            
            # Handle attachments (you'd need an Attachment model for broadcasts)
            # attachments = self.cleaned_data.get('attachments')
            # if attachments:
            #     for file in attachments:
            #         BroadcastAttachment.objects.create(...)
            
            # Add recipients based on recipient type
            recipient_type = self.cleaned_data.get('recipient_type')
            
            if recipient_type == 'all_students':
                recipients = User.objects.filter(user_type='student', is_active=True)
                broadcast.recipients.add(*recipients)
                broadcast.recipient_groups = ['all_students']
            
            elif recipient_type == 'all_executives':
                recipients = User.objects.filter(user_type='executive', is_active=True)
                broadcast.recipients.add(*recipients)
                broadcast.recipient_groups = ['all_executives']
            
            elif recipient_type == 'all_staff':
                recipients = User.objects.filter(user_type='staff', is_active=True)
                broadcast.recipients.add(*recipients)
                broadcast.recipient_groups = ['all_staff']
            
            elif recipient_type == 'by_level':
                levels = self.cleaned_data.get('target_levels')
                recipients = User.objects.filter(
                    user_type='student',
                    level__in=levels,
                    is_active=True
                )
                broadcast.recipients.add(*recipients)
                broadcast.recipient_groups = [f'level_{level}' for level in levels]
            
            elif recipient_type == 'by_program':
                program = self.cleaned_data.get('target_program')
                recipients = User.objects.filter(
                    user_type='student',
                    program_type=program,
                    is_active=True
                )
                broadcast.recipients.add(*recipients)
                broadcast.recipient_groups = [f'program_{program}']
            
            elif recipient_type == 'custom':
                recipients = self.cleaned_data.get('custom_recipients')
                broadcast.recipients.add(*recipients)
                broadcast.recipient_groups = ['custom']
            
            broadcast.save()
        
        return broadcast


# ========== NOTIFICATION FORMS ==========

class NotificationSettingsForm(forms.ModelForm):
    """
    Form for users to configure notification preferences
    """
    class Meta:
        model = NotificationPreference
        fields = (
            'email_messages', 'email_broadcasts', 'email_events', 'email_payments',
            'in_app_messages', 'in_app_broadcasts', 'in_app_events', 'in_app_payments',
            'email_digest', 'quiet_hours_start', 'quiet_hours_end'
        )
        widgets = {
            'email_messages': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_broadcasts': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_events': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_payments': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'in_app_messages': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'in_app_broadcasts': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'in_app_events': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'in_app_payments': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_digest': forms.Select(attrs={'class': 'form-select'}),
            'quiet_hours_start': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'quiet_hours_end': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('quiet_hours_start')
        end = cleaned_data.get('quiet_hours_end')
        
        if start and end and start >= end:
            raise ValidationError("Quiet hours end time must be after start time.")
        
        return cleaned_data


class NotificationFilterForm(forms.Form):
    """
    Form for filtering notifications
    """
    notification_type = forms.ChoiceField(
        choices=[('', 'All Types')] + list(Notification.NOTIFICATION_TYPES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    is_read = forms.ChoiceField(
        choices=[
            ('', 'All'),
            ('read', 'Read'),
            ('unread', 'Unread'),
        ],
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


# ========== CONVERSATION SEARCH FORM ==========

class ConversationSearchForm(forms.Form):
    """
    Form for searching conversations
    """
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search conversations...'
        })
    )
    unread_only = forms.BooleanField(
        required=False,
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


# ========== COMPLAINT/SUGGESTION FORMS ==========

class ComplaintForm(forms.ModelForm):
    """
    Form for submitting complaints/suggestions
    """
    attachments = MultipleFileField(
        required=False,
        label='Supporting Documents',
        help_text='Upload any relevant files (max 10MB each)'
    )
    
    class Meta:
        model = Complaint
        fields = ('complaint_type', 'subject', 'description', 'is_anonymous')
        widgets = {
            'complaint_type': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Brief summary of your complaint/suggestion'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Please provide details...'
            }),
            'is_anonymous': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def clean_attachments(self):
        """Validate attachments"""
        attachments = self.cleaned_data.get('attachments')
        
        if attachments:
            for file in attachments:
                if file.size > 10 * 1024 * 1024:
                    raise ValidationError(f"File {file.name} exceeds 10MB limit.")
        
        return attachments
    
    def save(self, commit=True):
        complaint = super().save(commit=False)
        complaint.user = self.user
        
        if commit:
            complaint.save()
            
            # Handle attachments
            attachments = self.cleaned_data.get('attachments')
            if attachments:
                for file in attachments:
                    ComplaintAttachment.objects.create(
                        complaint=complaint,
                        file=file,
                        filename=file.name
                    )
        
        return complaint


class ComplaintResponseForm(forms.ModelForm):
    """
    Form for responding to complaints (admin/executive only)
    """
    class Meta:
        model = ComplaintResponse
        fields = ('content',)
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Write your response...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.responder = kwargs.pop('responder', None)
        self.complaint = kwargs.pop('complaint', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        response = super().save(commit=False)
        response.responder = self.responder
        response.complaint = self.complaint
        
        if commit:
            response.save()
            
            # Update complaint status
            self.complaint.status = 'under_review'
            self.complaint.assigned_to = self.responder
            self.complaint.save()
        
        return response


class ComplaintStatusUpdateForm(forms.ModelForm):
    """
    Form for updating complaint status
    """
    class Meta:
        model = Complaint
        fields = ('status', 'assigned_to')
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_to'].queryset = User.objects.filter(
            user_type__in=['admin', 'staff', 'executive'],
            is_active=True
        )
        self.fields['assigned_to'].required = False
        self.fields['assigned_to'].empty_label = "Unassigned"
    
    def save(self, commit=True):
        complaint = super().save(commit=False)
        
        if complaint.status == 'resolved' and not complaint.resolved_at:
            complaint.resolved_at = timezone.now()
        
        if commit:
            complaint.save()
        
        return complaint