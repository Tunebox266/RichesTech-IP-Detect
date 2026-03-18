# complaints/forms.py
from django import forms
from .models import Complaint, ComplaintResponse

class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ['complaint_type', 'title', 'description', 'attachment']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        self.fields['attachment'].widget.attrs.update({'class': 'form-control-file'})

class ComplaintResponseForm(forms.ModelForm):
    class Meta:
        model = ComplaintResponse
        fields = ['message', 'attachment']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Type your response here...'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        self.fields['attachment'].widget.attrs.update({'class': 'form-control-file'})

class ComplaintStatusForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ['status']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].widget.attrs.update({'class': 'form-select'})