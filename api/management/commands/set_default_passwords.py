from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Set default passwords for users'

    def handle(self, *args, **kwargs):
        users = User.objects.all()
        count = 0
        
        for user in users:
            user.set_password('testpass123')
            user.save()
            count += 1
            self.stdout.write(f'Set password for user: {user.username}')
        
        self.stdout.write(self.style.SUCCESS(f'Successfully set passwords for {count} users'))
