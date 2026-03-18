# courses/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
import re

from .models import Course, CourseMaterial, CourseRegistration
from apps.accounts.models import User
from apps.core.models import AcademicSetting


class CourseForm(forms.ModelForm):
    """
    Form for creating and editing courses
    """
    class Meta:
        model = Course
        fields = ('code', 'title', 'level', 'semester', 'credit_hours', 'description', 'is_active')
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., BTML201'
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter course title'
            }),
            'level': forms.Select(attrs={'class': 'form-select'}),
            'semester': forms.Select(attrs={'class': 'form-select'}),
            'credit_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 6
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter course description (optional)'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_code(self):
        """Validate course code format"""
        code = self.cleaned_data.get('code')
        
        # Convert to uppercase
        code = code.upper()
        
        # Check format: should be letters followed by numbers
        if not re.match(r'^[A-Z]{2,4}\d{3,4}$', code):
            raise ValidationError(
                "Course code should be 2-4 letters followed by 3-4 numbers (e.g., BTML201)"
            )
        
        # Check uniqueness (case-insensitive)
        qs = Course.objects.filter(code__iexact=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        
        if qs.exists():
            raise ValidationError(f"Course with code {code} already exists.")
        
        return code
    
    def clean_credit_hours(self):
        """Validate credit hours"""
        credit_hours = self.cleaned_data.get('credit_hours')
        
        if credit_hours < 1 or credit_hours > 6:
            raise ValidationError("Credit hours must be between 1 and 6.")
        
        return credit_hours


class CourseMaterialForm(forms.ModelForm):
    """
    Form for uploading course materials
    """
    class Meta:
        model = CourseMaterial
        fields = ('course', 'title', 'material_type', 'file', 'description')
        widgets = {
            'course': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Chapter 1 Lecture Notes'
            }),
            'material_type': forms.Select(attrs={'class': 'form-select'}),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.ppt,.pptx,.doc,.docx,.xls,.xlsx,.txt'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Brief description of the material (optional)'
            }),
        }
    
    def clean_file(self):
        """Validate file type and size"""
        file = self.cleaned_data.get('file')
        
        if file:
            # Check file size (max 50MB)
            if file.size > 50 * 1024 * 1024:
                raise ValidationError("File size must be less than 50MB.")
            
            # Check file extension
            allowed_extensions = ['.pdf', '.ppt', '.pptx', '.doc', '.docx', '.xls', '.xlsx', '.txt']
            ext = file.name[file.name.rfind('.'):].lower()
            
            if ext not in allowed_extensions:
                raise ValidationError(
                    f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
                )
        
        return file


class CourseMaterialUpdateForm(forms.ModelForm):
    """
    Form for updating course material metadata (without file)
    """
    class Meta:
        model = CourseMaterial
        fields = ('title', 'material_type', 'description')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'material_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class CourseRegistrationForm(forms.Form):
    """
    Form for students to register for courses
    """
    courses = forms.ModelMultipleChoiceField(
        queryset=None,  # Will be set in __init__
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        self.student = kwargs.pop('student', None)
        self.academic_setting = kwargs.pop('academic_setting', None)
        super().__init__(*args, **kwargs)
        
        if self.student and self.academic_setting:
            # Get already registered courses
            registered = CourseRegistration.objects.filter(
                student=self.student,
                academic_setting=self.academic_setting
            ).values_list('course_id', flat=True)
            
            # Get available courses for student's level and current semester
            available_courses = Course.objects.filter(
                level=self.student.level,
                semester=self.academic_setting.current_semester,
                is_active=True
            ).exclude(id__in=registered)
            
            self.fields['courses'].queryset = available_courses
            
            # Add help text
            if not available_courses.exists():
                self.fields['courses'].help_text = "No courses available for registration at this time."
    
    def clean_courses(self):
        """Validate course selection"""
        courses = self.cleaned_data.get('courses')
        
        if courses and len(courses) > 10:  # Max 10 courses per semester
            raise ValidationError("You cannot register for more than 10 courses in a semester.")
        
        return courses


class CourseSearchForm(forms.Form):
    """
    Form for searching and filtering courses
    """
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by code or title...'
        })
    )
    level = forms.ChoiceField(
        choices=[('', 'All Levels')] + list(Course.LEVEL_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    semester = forms.ChoiceField(
        choices=[('', 'All Semesters')] + list(Course.SEMESTER_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    is_active = forms.ChoiceField(
        choices=[('', 'All'), ('true', 'Active Only'), ('false', 'Inactive Only')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class MaterialSearchForm(forms.Form):
    """
    Form for searching and filtering materials
    """
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search materials...'
        })
    )
    course = forms.ModelChoiceField(
        queryset=Course.objects.filter(is_active=True),
        required=False,
        empty_label="All Courses",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    material_type = forms.ChoiceField(
        choices=[('', 'All Types')] + list(CourseMaterial.MATERIAL_TYPES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    level = forms.ChoiceField(
        choices=[('', 'All Levels')] + list(Course.LEVEL_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    sort_by = forms.ChoiceField(
        choices=[
            ('-uploaded_at', 'Newest First'),
            ('uploaded_at', 'Oldest First'),
            ('title', 'Title A-Z'),
            ('-title', 'Title Z-A'),
            ('-downloads', 'Most Downloaded'),
        ],
        required=False,
        initial='-uploaded_at',
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class BulkCourseUploadForm(forms.Form):
    """
    Form for bulk uploading courses via CSV
    """
    file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv'
        }),
        help_text="Upload a CSV file with columns: code, title, level, semester, credit_hours (optional), description (optional)"
    )
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        
        if file:
            if not file.name.endswith('.csv'):
                raise ValidationError("Please upload a CSV file.")
            
            # Check file size (max 5MB)
            if file.size > 5 * 1024 * 1024:
                raise ValidationError("File size must be less than 5MB.")
        
        return file


class StudentCourseRegistrationForm(forms.Form):
    """
    Form for staff/admin to register students for courses
    """
    student = forms.ModelChoiceField(
        queryset=User.objects.filter(user_type__in=['student', 'executive']),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    courses = forms.ModelMultipleChoiceField(
        queryset=Course.objects.filter(is_active=True),
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 10}),
        required=True
    )
    academic_setting = forms.ModelChoiceField(
        queryset=AcademicSetting.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    
    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student')
        courses = cleaned_data.get('courses')
        academic_setting = cleaned_data.get('academic_setting')
        
        if student and courses and academic_setting:
            # Check for existing registrations
            existing = CourseRegistration.objects.filter(
                student=student,
                course__in=courses,
                academic_setting=academic_setting
            ).values_list('course__code', flat=True)
            
            if existing.exists():
                raise ValidationError(
                    f"Student already registered for: {', '.join(existing)}"
                )
        
        return cleaned_data


class CourseUnregistrationForm(forms.Form):
    """
    Form for unregistering from courses
    """
    course_registrations = forms.ModelMultipleChoiceField(
        queryset=None,  # Will be set in __init__
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=True
    )
    
    def __init__(self, *args, **kwargs):
        self.student = kwargs.pop('student', None)
        self.academic_setting = kwargs.pop('academic_setting', None)
        super().__init__(*args, **kwargs)
        
        if self.student and self.academic_setting:
            self.fields['course_registrations'].queryset = CourseRegistration.objects.filter(
                student=self.student,
                academic_setting=self.academic_setting
            ).select_related('course')
    
    def clean_course_registrations(self):
        registrations = self.cleaned_data.get('course_registrations')
        
        if not registrations:
            raise ValidationError("Please select at least one course to unregister.")
        
        return registrations


class CourseAssignmentForm(forms.Form):
    """
    Form for assigning lecturers to courses (staff/admin only)
    """
    course = forms.ModelChoiceField(
        queryset=Course.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    lecturer = forms.ModelChoiceField(
        queryset=User.objects.filter(user_type='staff', is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True,
        empty_label="Select Lecturer"
    )
    academic_setting = forms.ModelChoiceField(
        queryset=AcademicSetting.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    
    def clean(self):
        cleaned_data = super().clean()
        course = cleaned_data.get('course')
        lecturer = cleaned_data.get('lecturer')
        academic_setting = cleaned_data.get('academic_setting')
        
        # Note: You might want to add a model for course assignments
        # This is a placeholder for that functionality
        
        return cleaned_data


class CourseMaterialFilterForm(forms.Form):
    """
    Form for filtering course materials in a specific course
    """
    material_type = forms.ChoiceField(
        choices=[('', 'All Types')] + list(CourseMaterial.MATERIAL_TYPES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search materials...'
        })
    )
    sort_by = forms.ChoiceField(
        choices=[
            ('-uploaded_at', 'Newest First'),
            ('uploaded_at', 'Oldest First'),
            ('title', 'Title A-Z'),
            ('-title', 'Title Z-A'),
            ('-downloads', 'Most Downloaded'),
        ],
        required=False,
        initial='-uploaded_at',
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class CoursePrerequisiteForm(forms.Form):
    """
    Form for setting course prerequisites
    Note: You'll need to add a Prerequisite model to implement this
    """
    course = forms.ModelChoiceField(
        queryset=Course.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    prerequisite_courses = forms.ModelMultipleChoiceField(
        queryset=Course.objects.filter(is_active=True),
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 8}),
        required=False
    )
    
    def clean(self):
        cleaned_data = super().clean()
        course = cleaned_data.get('course')
        prerequisites = cleaned_data.get('prerequisite_courses')
        
        if course and prerequisites and course in prerequisites:
            raise ValidationError("A course cannot be a prerequisite for itself.")
        
        return cleaned_data


class CourseLevelTransferForm(forms.Form):
    """
    Form for transferring students to new level
    """
    current_level = forms.ChoiceField(
        choices=Course.LEVEL_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    new_level = forms.ChoiceField(
        choices=Course.LEVEL_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    academic_setting = forms.ModelChoiceField(
        queryset=AcademicSetting.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    students = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(user_type__in=['student', 'executive']),
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 10}),
        required=True
    )
    
    def clean(self):
        cleaned_data = super().clean()
        current_level = cleaned_data.get('current_level')
        new_level = cleaned_data.get('new_level')
        
        if current_level and new_level and current_level >= new_level:
            raise ValidationError("New level must be higher than current level.")
        
        return cleaned_data


# ========== AJAX FORMS ==========

class QuickCourseRegistrationForm(forms.Form):
    """
    Simplified form for quick course registration via AJAX
    """
    course_id = forms.IntegerField(widget=forms.HiddenInput())
    
    def clean_course_id(self):
        course_id = self.cleaned_data.get('course_id')
        
        try:
            course = Course.objects.get(id=course_id, is_active=True)
        except Course.DoesNotExist:
            raise ValidationError("Invalid course selected.")
        
        return course_id


class QuickMaterialUploadForm(forms.ModelForm):
    """
    Simplified form for quick material upload via AJAX
    """
    class Meta:
        model = CourseMaterial
        fields = ('course', 'title', 'material_type', 'file')
        widgets = {
            'course': forms.HiddenInput(),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Material title'}),
            'material_type': forms.Select(attrs={'class': 'form-select'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
        }

# courses/forms.py
from django import forms
from .models import MaterialComment

class MaterialCommentForm(forms.ModelForm):
    class Meta:
        model = MaterialComment
        fields = ['comment']  # Just the text field
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Add a comment...'})
        }