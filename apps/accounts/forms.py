# accounts/forms.py
from django import forms
from django.contrib.auth.forms import (
    UserCreationForm, UserChangeForm, 
    AuthenticationForm, PasswordChangeForm,
    PasswordResetForm, SetPasswordForm
)
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.utils import timezone
import re

from .models import (
    User, StudentExecutive, ExecutiveMeeting, ExecutiveTask, 
    ExecutiveDiscussion, DiscussionComment, ActivityLog, MeetingAttendance
)

# ========== CUSTOM USER FORMS ==========

class CustomUserCreationForm(UserCreationForm):
    """
    Form for creating new users (Admin use)
    """
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='Password will be auto-generated if left blank',
        required=False
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'user_type', 
                 'program_type', 'year_of_admission', 'level', 'phone_number',
                 'date_of_birth', 'address', 'profile_image', 'is_active')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'user_type': forms.Select(attrs={'class': 'form-select'}),
            'program_type': forms.Select(attrs={'class': 'form-select'}),
            'year_of_admission': forms.NumberInput(attrs={'class': 'form-control'}),
            'level': forms.Select(attrs={'class': 'form-select'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].required = False
        self.fields['password2'].required = False
        
        # Make some fields required based on user type
        if 'user_type' in self.data:
            if self.data.get('user_type') in ['student', 'executive']:
                self.fields['program_type'].required = True
                self.fields['year_of_admission'].required = True
                self.fields['level'].required = True
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password1 != password2:
            raise ValidationError("Passwords don't match")
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Set password if provided, otherwise generate random password
        if self.cleaned_data['password1']:
            user.set_password(self.cleaned_data['password1'])
        else:
            # Generate random password
            import secrets
            import string
            alphabet = string.ascii_letters + string.digits
            password = ''.join(secrets.choice(alphabet) for i in range(12))
            user.set_password(password)
            user.requires_password_change = True
            # Store password in session or email to user
            self.temp_password = password
        
        if commit:
            user.save()
        return user


class CustomUserChangeForm(UserChangeForm):
    """
    Form for updating user information
    """
    password = None  # Remove password field from change form
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'user_type',
                 'program_type', 'year_of_admission', 'level', 'phone_number',
                 'date_of_birth', 'address', 'profile_image', 'is_active')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'user_type': forms.Select(attrs={'class': 'form-select'}),
            'program_type': forms.Select(attrs={'class': 'form-select'}),
            'year_of_admission': forms.NumberInput(attrs={'class': 'form-control'}),
            'level': forms.Select(attrs={'class': 'form-select'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


# ========== LOGIN FORMS ==========

class CustomAuthenticationForm(AuthenticationForm):
    """
    Custom login form with additional validation
    """
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username or Student/Staff ID'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )
    remember_me = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        
        if username and password:
            # Try to find user by student_id or staff_id if username doesn't match
            try:
                user = User.objects.get(student_id=username)
                username = user.username
            except User.DoesNotExist:
                try:
                    user = User.objects.get(staff_id=username)
                    username = user.username
                except User.DoesNotExist:
                    pass
            
            self.user_cache = authenticate(self.request, username=username, password=password)
            
            if self.user_cache is None:
                # Log failed attempt
                from .models import LoginAttempt
                LoginAttempt.objects.create(
                    username=username,
                    ip_address=self.request.META.get('REMOTE_ADDR'),
                    successful=False
                )
                raise ValidationError("Invalid username or password.")
            else:
                # Check if account is locked
                if self.user_cache.account_locked_until and self.user_cache.account_locked_until > timezone.now():
                    raise ValidationError(
                        f"Account is locked until {self.user_cache.account_locked_until.strftime('%Y-%m-%d %H:%M')}"
                    )
                
                # Log successful attempt
                from .models import LoginAttempt, ActivityLog
                LoginAttempt.objects.create(
                    username=username,
                    ip_address=self.request.META.get('REMOTE_ADDR'),
                    successful=True
                )
                ActivityLog.objects.create(
                    user=self.user_cache,
                    action_type='login',
                    ip_address=self.request.META.get('REMOTE_ADDR'),
                    details={'username': username}
                )
        
        return self.cleaned_data


# ========== PASSWORD MANAGEMENT FORMS ==========

class CustomPasswordChangeForm(PasswordChangeForm):
    """
    Custom password change form with strength validation
    """
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Current Password'})
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New Password'}),
        help_text='Password must be at least 8 characters and contain letters and numbers'
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm New Password'})
    )
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
    
    def clean_new_password1(self):
        password = self.cleaned_data.get('new_password1')
        
        # Password strength validation
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        
        if not re.search(r'[A-Za-z]', password) or not re.search(r'[0-9]', password):
            raise ValidationError("Password must contain both letters and numbers.")
        
        return password
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.requires_password_change = False
        
        if commit:
            user.save()
            
            # Log password change
            if self.request:
                from .models import ActivityLog
                ActivityLog.objects.create(
                    user=user,
                    action_type='password_change',
                    ip_address=self.request.META.get('REMOTE_ADDR'),
                    details={'action': 'password_changed'}
                )
        
        return user


class CustomPasswordResetForm(PasswordResetForm):
    """
    Custom password reset form
    """
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email'})
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        
        # Check if email exists
        if not User.objects.filter(email=email).exists():
            raise ValidationError("No user found with this email address.")
        
        return email


class CustomSetPasswordForm(SetPasswordForm):
    """
    Custom set password form
    """
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New Password'}),
        label="New password"
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm New Password'}),
        label="Confirm password"
    )


# ========== PROFILE FORMS ==========

class StudentProfileForm(forms.ModelForm):
    """
    Form for students to update their profile
    """
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone_number', 
                 'date_of_birth', 'address', 'profile_image')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'readonly': True}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
        }


class StaffProfileForm(forms.ModelForm):
    """
    Form for staff to update their profile
    """
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone_number', 
                 'profile_image')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'readonly': True}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
        }


# ========== EXECUTIVE FORMS ==========

class StudentExecutiveForm(forms.ModelForm):
    """
    Form for creating/updating student executive profiles
    """
    class Meta:
        model = StudentExecutive
        fields = ('position', 'executive_level', 'tenure_start_date', 'tenure_end_date',
                 'manifesto', 'achievements', 'executive_image', 'signature',
                 'official_email', 'office_location', 'office_hours',
                 'can_manage_events', 'can_upload_materials', 'can_send_announcements',
                 'can_take_attendance', 'can_manage_complaints', 'can_view_financial_reports')
        widgets = {
            'position': forms.Select(attrs={'class': 'form-select'}),
            'executive_level': forms.Select(attrs={'class': 'form-select'}),
            'tenure_start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'tenure_end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'manifesto': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'achievements': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'executive_image': forms.FileInput(attrs={'class': 'form-control'}),
            'signature': forms.FileInput(attrs={'class': 'form-control'}),
            'official_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'office_location': forms.TextInput(attrs={'class': 'form-control'}),
            'office_hours': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Mon-Fri 9AM-4PM'}),
            'can_manage_events': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_upload_materials': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_send_announcements': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_take_attendance': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_manage_complaints': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_view_financial_reports': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('tenure_start_date')
        end_date = cleaned_data.get('tenure_end_date')
        
        if start_date and end_date and end_date <= start_date:
            raise ValidationError("End date must be after start date.")
        
        return cleaned_data


class ExecutiveMeetingForm(forms.ModelForm):
    """
    Form for creating/updating executive meetings
    """
    participants = forms.ModelMultipleChoiceField(
        queryset=StudentExecutive.objects.filter(tenure_status='active'),
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
        required=False
    )
    
    class Meta:
        model = ExecutiveMeeting
        fields = ('title', 'meeting_type', 'description', 'date', 'start_time', 
                 'end_time', 'venue', 'is_virtual', 'meeting_link', 'agenda',
                 'minutes', 'attachments', 'requires_attendance')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'meeting_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'venue': forms.TextInput(attrs={'class': 'form-control'}),
            'is_virtual': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'meeting_link': forms.URLInput(attrs={'class': 'form-control'}),
            'agenda': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'minutes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'attachments': forms.FileInput(attrs={'class': 'form-control'}),
            'requires_attendance': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        is_virtual = cleaned_data.get('is_virtual')
        meeting_link = cleaned_data.get('meeting_link')
        
        if start_time and end_time and end_time <= start_time:
            raise ValidationError("End time must be after start time.")
        
        if is_virtual and not meeting_link:
            raise ValidationError("Meeting link is required for virtual meetings.")
        
        return cleaned_data


class ExecutiveTaskForm(forms.ModelForm):
    """
    Form for creating/updating executive tasks
    """
    class Meta:
        model = ExecutiveTask
        fields = ('title', 'description', 'assigned_to', 'priority', 
                 'due_date', 'related_to_meeting', 'attachments')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'related_to_meeting': forms.Select(attrs={'class': 'form-select'}),
            'attachments': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def clean_due_date(self):
        due_date = self.cleaned_data.get('due_date')
        if due_date and due_date < timezone.now().date():
            raise ValidationError("Due date cannot be in the past.")
        return due_date


class ExecutiveTaskUpdateForm(forms.ModelForm):
    """
    Form for updating task status and feedback
    """
    class Meta:
        model = ExecutiveTask
        fields = ('status', 'feedback')
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'feedback': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ExecutiveDiscussionForm(forms.ModelForm):
    """
    Form for creating discussion topics
    """
    class Meta:
        model = ExecutiveDiscussion
        fields = ('title', 'content', 'is_announcement', 'attachments')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'is_announcement': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'attachments': forms.FileInput(attrs={'class': 'form-control'}),
        }


class DiscussionCommentForm(forms.ModelForm):
    """
    Form for adding comments to discussions
    """
    class Meta:
        model = DiscussionComment
        fields = ('content', 'attachments')
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Write your comment...'}),
            'attachments': forms.FileInput(attrs={'class': 'form-control'}),
        }


class MeetingAttendanceForm(forms.Form):
    """
    Form for meeting check-in
    """
    meeting_code = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter meeting code'})
    )
    
    def clean_meeting_code(self):
        code = self.cleaned_data.get('meeting_code')
        try:
            meeting = ExecutiveMeeting.objects.get(meeting_code=code, date=timezone.now().date())
            
            # Check if meeting is ongoing
            current_time = timezone.now().time()
            if not (meeting.start_time <= current_time <= meeting.end_time):
                raise ValidationError("Meeting is not currently in session.")
            
            return code
        except ExecutiveMeeting.DoesNotExist:
            raise ValidationError("Invalid meeting code for today.")


# ========== BULK UPLOAD FORMS ==========

class BulkStudentUploadForm(forms.Form):
    """
    Form for bulk uploading students via CSV/Excel
    """
    file = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv,.xlsx,.xls'}),
        help_text="Upload CSV or Excel file with columns: first_name, last_name, email, program_type, year_of_admission, level"
    )
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            ext = file.name.split('.')[-1].lower()
            if ext not in ['csv', 'xlsx', 'xls']:
                raise ValidationError("Please upload a CSV or Excel file.")
        return file


# ========== SEARCH FORMS ==========

class UserSearchForm(forms.Form):
    """
    Form for searching users
    """
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search by name, ID, or email...'})
    )
    user_type = forms.ChoiceField(
        choices=[('', 'All Types')] + list(User.USER_TYPES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    level = forms.ChoiceField(
        choices=[('', 'All Levels'), (100, '100'), (200, '200'), (300, '300'), (400, '400')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    program_type = forms.ChoiceField(
        choices=[('', 'All Programs')] + list(User.PROGRAM_TYPES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    is_active = forms.ChoiceField(
        choices=[('', 'All'), ('true', 'Active'), ('false', 'Inactive')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


# ========== PROFILE IMAGE FORM ==========

class ProfileImageForm(forms.ModelForm):
    """
    Simple form for updating just the profile image
    """
    class Meta:
        model = User
        fields = ('profile_image',)
        widgets = {
            'profile_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }
    
    def clean_profile_image(self):
        image = self.cleaned_data.get('profile_image')
        if image:
            # Check file size (max 2MB)
            if image.size > 2 * 1024 * 1024:
                raise ValidationError("Image file too large (max 2MB).")
            
            # Check file extension
            ext = image.name.split('.')[-1].lower()
            if ext not in ['jpg', 'jpeg', 'png', 'gif']:
                raise ValidationError("Please upload a valid image file (jpg, jpeg, png, gif).")
        
        return image


