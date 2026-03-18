# attendance/forms.py
from django import forms
from .models import AttendanceSession

class AttendanceSessionForm(forms.ModelForm):
    class Meta:
        model = AttendanceSession
        fields = ['title', 'session_type', 'event', 'date', 'start_time', 'end_time', 'venue']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        # Limit events to those created by user or all if admin/staff
        user = kwargs.get('initial', {}).get('user')
        if user and user.user_type not in ['admin', 'staff']:
            self.fields['event'].queryset = Event.objects.filter(created_by=user)

class ManualAttendanceForm(forms.Form):
    session = forms.ModelChoiceField(
        queryset=AttendanceSession.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    student_id = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter Student ID'
        })
    )