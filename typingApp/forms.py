from django import forms
from tinymce.widgets import TinyMCE
from .models import JobPost,BlogPost
class JobPostForm(forms.ModelForm):
    class Meta:
        model = JobPost
        fields = ['title', 'description', 'company', 'location', 'image']  # Exclude 'posted_date' as it's auto
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': TinyMCE(),
            'company': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
        }

class BlogPostForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = ['title', 'description', 'image']  # Exclude 'posted_date' as it's auto
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': TinyMCE(),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
        }