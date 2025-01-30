from django.db import migrations, models
import django.utils.timezone

class Migration(migrations.Migration):
    dependencies = [
        ('api', '0012_add_tokesignoff_shift_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='tokesignoff',
            name='signed_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
