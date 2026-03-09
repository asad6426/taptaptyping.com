from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class SignUpForm(forms.ModelForm):
    """Signup form with NO password requirements - খুব সহজ password দিতে পারবেন"""
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username',
            'id': 'username'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email Address',
            'id': 'email'
        })
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password (যেকোনো password - 1, abc, test যেকোনো কিছু)',
            'id': 'password'
        })
    )
    confirm_password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm Password',
            'id': 'confirm_password'
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError('এই username আগে থেকে আছে / This username is already taken.')
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('এই email আগে থেকে registered / This email is already registered.')
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        # শুধুমাত্র check করবে password দুইটা same কিনা
        # কোনো length বা complexity check নেই!
        # Password "1" বা "a" হলেও চলবে!
        if password and confirm_password:
            if password != confirm_password:
                raise ValidationError('Password মিলছে না / Passwords do not match.')
        
        return cleaned_data


class LoginForm(forms.Form):
    """Login form"""
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username',
            'id': 'username'
        })
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'id': 'password'
        })
    )


class ForgotPasswordForm(forms.Form):
    """Forgot password form"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'আপনার email address / Enter your email address',
            'id': 'email'
        })
    )


class ResetPasswordForm(forms.Form):
    """Reset password form - কোনো validation নেই, একদম সহজ"""
    new_password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New Password (যেকোনো কিছু)',
            'id': 'new_password'
        })
    )
    confirm_password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm New Password',
            'id': 'confirm_password'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        # শুধু match করলেই হবে - আর কিছু লাগবে না
        if new_password and confirm_password:
            if new_password != confirm_password:
                raise ValidationError('Password মিলছে না / Passwords do not match.')
        
        return cleaned_data