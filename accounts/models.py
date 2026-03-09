from django.db import models
from django.contrib.auth.models import User

# Using Django's built-in User model
# You can extend it here if needed in the future

# Example: Custom User Profile model (optional)
# class UserProfile(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
#     phone_number = models.CharField(max_length=15, blank=True, null=True)
#     address = models.TextField(blank=True, null=True)
#     date_of_birth = models.DateField(blank=True, null=True)
#     profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
#     
#     def __str__(self):
#         return f"{self.user.username}'s Profile"