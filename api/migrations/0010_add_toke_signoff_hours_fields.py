from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('api', '0009_casino_day_end_casino_day_start_casino_grave_end_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='tokesignoff',
            name='scheduled_hours',
            field=models.DecimalField(
                max_digits=5,
                decimal_places=2,
                default=8.00,
                help_text='Scheduled shift duration in hours'
            ),
        ),
        migrations.AddField(
            model_name='tokesignoff',
            name='actual_hours',
            field=models.DecimalField(
                max_digits=5,
                decimal_places=2,
                null=True,
                blank=True,
                help_text='Actual hours worked (updated if early out authorized)'
            ),
        ),
        migrations.AddField(
            model_name='tokesignoff',
            name='original_hours',
            field=models.DecimalField(
                max_digits=5,
                decimal_places=2,
                null=True,
                blank=True,
                help_text='Original hours before any adjustments'
            ),
        ),
        migrations.RenameField(
            model_name='tokesignoff',
            old_name='hours',
            new_name='toke_hours',
        ),
    ]
