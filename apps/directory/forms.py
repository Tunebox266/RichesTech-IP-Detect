# apps/directory/forms.py

from django import forms
from .models import StudentIDCard

class StudentIDCardForm(forms.ModelForm):
    class Meta:
        model = StudentIDCard
        fields = [
            'blood_group', 'valid_until', 'student_signature',
            'emergency_contact_name', 'emergency_relationship',
            'emergency_phone', 'emergency_address',
            'allergies', 'medical_conditions'
        ]
        widgets = {
            'valid_until': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'blood_group': forms.Select(attrs={'class': 'form-select'}),
            'student_signature': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/png,image/jpeg'}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'}),
            'emergency_relationship': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Parent, Spouse'}),
            'emergency_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+233 XX XXX XXXX'}),
            'emergency_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'allergies': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'List any allergies'}),
            'medical_conditions': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'List important medical conditions'}),
        }


from django import forms
from .models import PastQuestion, StudentHandbook, AcademicCalendar

class PastQuestionForm(forms.ModelForm):
    class Meta:
        model = PastQuestion
        fields = ['title', 'course_code', 'course_name', 'level', 'semester', 
                  'academic_year', 'exam_year', 'file', 'is_approved']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., End of Semester Examination'}),
            'course_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., BTML201'}),
            'course_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Course title (optional)'}),
            'level': forms.Select(attrs={'class': 'form-select'}),
            'semester': forms.Select(attrs={'class': 'form-select'}),
            'academic_year': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 2024/2025'}),
            'exam_year': forms.NumberInput(attrs={'class': 'form-control', 'min': 2000, 'max': 2100}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'is_approved': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class PastQuestionSearchForm(forms.Form):
    query = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Search by course code or title...'
    }))
    level = forms.ChoiceField(choices=[('', 'All Levels'), (100, 'Level 100'), (200, 'Level 200'), (300, 'Level 300'), (400, 'Level 400')], 
                              required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    semester = forms.ChoiceField(choices=[('', 'All Semesters'), (1, 'First Semester'), (2, 'Second Semester')],
                                required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    year = forms.ChoiceField(required=False, widget=forms.Select(attrs={'class': 'form-select'}))


class StudentHandbookForm(forms.ModelForm):
    class Meta:
        model = StudentHandbook
        fields = ['title', 'version', 'description', 'file', 'cover_image', 'is_current', 'effective_date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Student Handbook'}),
            'version': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 2024 Edition'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'cover_image': forms.FileInput(attrs={'class': 'form-control'}),
            'is_current': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'effective_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class AcademicCalendarForm(forms.ModelForm):
    class Meta:
        model = AcademicCalendar
        fields = ['title', 'event_type', 'description', 'start_date', 'end_date', 
                  'is_all_day', 'start_time', 'end_time', 'academic_year', 
                  'semester', 'level', 'venue', 'is_important']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'event_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_all_day': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'academic_year': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 2024/2025'}),
            'semester': forms.Select(attrs={'class': 'form-select'}),
            'level': forms.Select(attrs={'class': 'form-select'}),
            'venue': forms.TextInput(attrs={'class': 'form-control'}),
            'is_important': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class AcademicCalendarFilterForm(forms.Form):
    year = forms.ChoiceField(required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    month = forms.ChoiceField(required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    
    # FIXED: Convert tuple to list by casting
    event_type = forms.ChoiceField(
        choices=[('', 'All Types')] + list(AcademicCalendar.EVENT_TYPES), 
        required=False, 
        widget=forms.Select(attrs={'class': 'form-select'})
    )