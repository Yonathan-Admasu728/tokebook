# Generated by Django 5.1.5 on 2025-01-22 09:54

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_alter_dealervacation_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='shift',
            field=models.IntegerField(blank=True, choices=[(1, 'Day'), (2, 'Swing'), (3, 'Grave')], null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(3)]),
        ),
    ]
