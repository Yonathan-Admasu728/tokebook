from django.db import migrations

def update_casino_manager_flags(apps, schema_editor):
    User = apps.get_model('api', 'User')
    for user in User.objects.filter(role='CASINO_MANAGER'):
        user.has_pencil_flag = True
        user.pencil_id = user.employee_id
        user.save()

def reverse_flag_update(apps, schema_editor):
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('api', '0007_update_casino_manager_pencils'),
    ]

    operations = [
        migrations.RunPython(update_casino_manager_flags, reverse_flag_update),
    ]
