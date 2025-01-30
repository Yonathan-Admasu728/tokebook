from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('api', '0011_alter_tokesignoff_toke_hours'),
    ]

    operations = [
        migrations.AddField(
            model_name='tokesignoff',
            name='shift_date',
            field=models.DateField(null=True, blank=True),
        ),
    ]
