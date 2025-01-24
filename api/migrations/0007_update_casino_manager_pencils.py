from django.db import migrations

def assign_pencils_to_casino_managers(apps, schema_editor):
    User = apps.get_model('api', 'User')
    for user in User.objects.filter(role='CASINO_MANAGER', pencil_id__isnull=True):
        user.has_pencil_flag = True
        user.pencil_id = user.employee_id
        user.save()

def reverse_pencil_assignment(apps, schema_editor):
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('api', '0006_user_pencil_id'),
    ]

    operations = [
        migrations.RunPython(assign_pencils_to_casino_managers, reverse_pencil_assignment),
    ]
