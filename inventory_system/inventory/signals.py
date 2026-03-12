from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    # Create profile if it does not exist
    UserProfile.objects.get_or_create(user=instance)

    # Update profile safely
    instance.userprofile.save()
