# Generated by Django 5.1.5 on 2025-01-22 05:16

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='earlyoutrequest',
            name='authorized_by_pencil',
        ),
        migrations.RemoveField(
            model_name='user',
            name='pencil_id',
        ),
        migrations.RemoveField(
            model_name='user',
            name='pencil_suspended_until',
        ),
        migrations.AddField(
            model_name='discrepancy',
            name='verification_notes',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='employee_id',
            field=models.CharField(blank=True, max_length=10, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(choices=[('DEALER', 'Dealer'), ('SUPERVISOR', 'Supervisor'), ('TOKE_MANAGER', 'Toke Manager'), ('CASINO_MANAGER', 'Casino Manager'), ('ACCOUNTING', 'Accounting'), ('ADMIN', 'Admin')], default='DEALER', max_length=20),
        ),
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('action', models.CharField(max_length=255)),
                ('model_name', models.CharField(default='unknown', max_length=50)),
                ('record_id', models.CharField(blank=True, max_length=50, null=True)),
                ('changes', models.JSONField(default=dict)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('casino', models.CharField(blank=True, max_length=100, null=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='DealerVacation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['start_date', 'end_date'],
            },
        ),
    ]
