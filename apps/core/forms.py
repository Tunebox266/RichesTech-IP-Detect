from django import forms
from .models import Announcement, ContactMessage, FAQ
from django.core.validators import EmailValidator


class ContactForm(forms.ModelForm):
    """Form for contact page submissions"""
    
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'phone', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Your full name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'your.email@example.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+233 XX XXX XXXX (optional)'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'What is this regarding?'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Your message...'
            }),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        validator = EmailValidator(message="Please enter a valid email address.")
        validator(email)
        return email


class FAQSearchForm(forms.Form):
    """Form for searching FAQs"""
    query = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Search FAQs...'
    }))
    category = forms.ChoiceField(required=False, choices=[('', 'All Categories')] + list(FAQ.CATEGORY_CHOICES), widget=forms.Select(attrs={
        'class': 'form-select'
    }))


class QuickContactForm(forms.Form):
    """Quick contact form for footer"""
    name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Your name'
    }))
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Your email'
    }))
    message = forms.CharField(widget=forms.Textarea(attrs={
        'class': 'form-control',
        'rows': 3,
        'placeholder': 'Your message'
    }))


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = [
            'title', 'content', 'image', 'attachment',
            'priority', 'target_groups', 'expiry_date', 'is_pinned'
        ]
        widgets = {
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'priority': forms.Select(),
            'target_groups': forms.Select(),
        }


from django import forms
from .models import PrivacyPolicy, TermsOfService

class PrivacyPolicyForm(forms.ModelForm):
    class Meta:
        model = PrivacyPolicy
        fields = ['title', 'content', 'version', 'effective_date', 'is_current']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 15}),
            'version': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., v1.0, 2024-01'}),
            'effective_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_current': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class TermsOfServiceForm(forms.ModelForm):
    class Meta:
        model = TermsOfService
        fields = ['title', 'content', 'version', 'effective_date', 'is_current']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 15}),
            'version': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., v1.0, 2024-01'}),
            'effective_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_current': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }