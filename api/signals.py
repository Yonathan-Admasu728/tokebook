from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import User

@receiver(pre_save, sender=User)
def auto_set_pencil_flag(sender, instance, **kwargs):
    """
    Automatically set has_pencil_flag to True when a user's role is set to CASINO_MANAGER
    """
    if instance.role == 'CASINO_MANAGER':
        instance.has_pencil_flag = True

@receiver(post_save, sender=User)
def ensure_casino_manager_pencil_flag(sender, instance, created, **kwargs):
    """
    Ensure existing casino managers have pencil flag set to True
    """
    if not created and instance.role == 'CASINO_MANAGER' and not instance.has_pencil_flag:
        User.objects.filter(id=instance.id).update(has_pencil_flag=True)
