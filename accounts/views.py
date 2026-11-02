from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from .forms import SignUpForm, LoginForm, ForgotPasswordForm, ResetPasswordForm


def signup_view(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('leaderboard')
    
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            
            # Log the user in after signup
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, 'অ্যাকাউন্ট সফলভাবে তৈরি হয়েছে! / Account created successfully!')
            return redirect('leaderboard')
        else:
            messages.error(request, 'ভুল আছে, আবার চেষ্টা করুন / Please correct the errors.')
    else:
        form = SignUpForm()
    
    return render(request, 'signup.html', {'form': form})


def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('leaderboard')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'স্বাগতম, {user.username}! / Welcome back, {user.username}!')
                next_url = request.GET.get('next', 'leaderboard')
                return redirect(next_url)
            else:
                messages.error(request, 'Username বা Password ভুল আছে / Invalid username or password.')
    else:
        form = LoginForm()
    
    return render(request, 'login.html', {'form': form})


@login_required
def logout_view(request):
    """User logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')


def forgot_password_view(request):
    """Forgot password view - sends reset email"""
    if request.user.is_authenticated:
        return redirect('leaderboard')
    
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                
                # Generate password reset token
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                
                # Create reset link
                reset_link = request.build_absolute_uri(
                    reverse('reset_password', kwargs={'uidb64': uid, 'token': token})
                )
                
                # Send email
                subject = 'Password Reset Request'
                message = f'''
Hello {user.username},

You requested to reset your password. Click the link below to reset it:

{reset_link}

If you didn't request this, please ignore this email.

Thanks,
The Team
                '''
                
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                
                messages.success(request, 'Password reset link has been sent to your email.')
                return redirect('login')
            except User.DoesNotExist:
                messages.error(request, 'No account found with this email address.')
    else:
        form = ForgotPasswordForm()
    
    return render(request, 'forgot_password.html', {'form': form})


def reset_password_view(request, uidb64, token):
    """Reset password view - validates token and resets password"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = ResetPasswordForm(request.POST)
            if form.is_valid():
                new_password = form.cleaned_data['new_password']
                user.set_password(new_password)
                user.save()
                messages.success(request, 'Your password has been reset successfully. You can now login.')
                return redirect('login')
        else:
            form = ResetPasswordForm()
        
        return render(request, 'reset_password.html', {'form': form, 'validlink': True})
    else:
        messages.error(request, 'The password reset link is invalid or has expired.')
        return render(request, 'reset_password.html', {'validlink': False})


# @login_required
# def home_view(request):
#     """Home page view - accessible only to logged in users"""
#     return render(request, 'home.html')