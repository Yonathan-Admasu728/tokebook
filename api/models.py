from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
from django.utils import timezone

class User(AbstractUser):
    ROLE_CHOICES = [
        ('DEALER', 'Dealer'),
        ('SUPERVISOR', 'Supervisor'),
        ('TOKE_MANAGER', 'Toke Manager'),
        ('CASINO_MANAGER', 'Casino Manager'),
        ('ACCOUNTING', 'Accounting'),
        ('ADMIN', 'Admin'),
    ]

    employee_id = models.CharField(max_length=10, unique=True, null=True, blank=True)  # 800 number
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='DEALER')
    casino = models.CharField(max_length=100, null=True, blank=True)  # Keep as CharField to match initial migration
    has_pencil_flag = models.BooleanField(default=False)
    pencil_id = models.CharField(max_length=10, unique=True, null=True, blank=True)
    shift = models.IntegerField(
        choices=[(1, 'Day'), (2, 'Swing'), (3, 'Grave')],
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(3)]
    )
    archived_at = models.DateTimeField(null=True, blank=True)
    archived_by = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='archived_users'
    )

    class Meta:
        db_table = 'auth_user'

    def save(self, *args, **kwargs):
        # If user is a casino manager, ensure they have pencil flag and ID
        if self.role == 'CASINO_MANAGER':
            self.has_pencil_flag = True
            # Always use employee ID as pencil ID for casino managers
            self.pencil_id = self.employee_id
            
        # Ensure username matches employee_id
        if self.employee_id and not self.username:
            self.username = self.employee_id
            
        # If this is a new user (no ID yet), ensure password is hashed
        if not self.id and self.password and not self.password.startswith(('pbkdf2_sha256$', 'bcrypt$', 'argon2')):
            self.set_password(self.password)
            
        super().save(*args, **kwargs)

    def __str__(self):
        if self.employee_id:
            return f"{self.get_full_name()} ({self.employee_id})"
        return self.get_full_name() or self.username

class Casino(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    
    # Shift timing configuration
    grave_start = models.TimeField(default='01:30')  # 1:30 AM
    grave_end = models.TimeField(default='09:30')    # 9:30 AM
    day_start = models.TimeField(default='09:30')    # 9:30 AM
    day_end = models.TimeField(default='17:30')      # 5:30 PM
    swing_start = models.TimeField(default='17:30')  # 5:30 PM
    swing_end = models.TimeField(default='01:30')    # 1:30 AM

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_current_shift(self):
        """
        Determines the current shift based on casino's shift configuration
        Returns: 'day', 'swing', or 'grave'
        """
        def time_to_minutes(t):
            return t.hour * 60 + t.minute

        current_time = timezone.localtime().time()
        current_minutes = time_to_minutes(current_time)
        
        # Convert all shift times to minutes
        grave_start = time_to_minutes(self.grave_start)  # 90 (1:30 AM)
        grave_end = time_to_minutes(self.grave_end)      # 570 (9:30 AM)
        day_start = time_to_minutes(self.day_start)      # 570 (9:30 AM)
        day_end = time_to_minutes(self.day_end)          # 1050 (5:30 PM)
        swing_start = time_to_minutes(self.swing_start)   # 1050 (5:30 PM)
        swing_end = time_to_minutes(self.swing_end)       # 90 (1:30 AM)

        # Day shift: 9:30 AM (570) to 5:30 PM (1050)
        if day_start <= current_minutes < day_end:
            return 'day'
            
        # Grave shift: 1:30 AM (90) to 9:30 AM (570)
        if grave_start <= current_minutes < grave_end:
            return 'grave'
            
        # Swing shift: 5:30 PM (1050) to 1:30 AM (90)
        # If we're not in day or grave shift, we must be in swing shift
        return 'swing'

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class Tokes(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField()
    finalized = models.BooleanField(default=False)
    is_collection_day = models.BooleanField(default=True, help_text='True if this is a collection day, False if distribution day')
    per_hour_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        verbose_name_plural = 'Tokes'

    def __str__(self):
        return f"Tokes for {self.date}"

class TokeSignOff(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    toke = models.ForeignKey(Tokes, on_delete=models.CASCADE)
    toke_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Final toke distribution hours'
    )
    scheduled_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=8.00,
        help_text='Scheduled shift duration in hours'
    )
    actual_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Actual hours worked (updated if early out authorized)'
    )
    original_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Original hours before any adjustments'
    )
    shift_date = models.DateField(null=True, blank=True)
    shift_start = models.TimeField(null=True, blank=True)
    shift_end = models.TimeField(null=True, blank=True)
    signed_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # When first created, set actual_hours to scheduled_hours
        if not self.pk:  # New instance
            self.actual_hours = self.scheduled_hours
            self.original_hours = self.scheduled_hours
            # Set shift_date from toke's date if not provided
            if not hasattr(self, 'shift_date') and self.toke:
                self.shift_date = self.toke.date
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'toke']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.toke.date}"

class DealerVacation(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('DENIED', 'Denied'),
        ('CANCELLED', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vacations')
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    notes = models.TextField(null=True, blank=True)
    
    # Approval fields
    approved_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='approved_vacations'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date', '-end_date']

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.start_date} - {self.end_date}) - {self.status}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.end_date < self.start_date:
            raise ValidationError('End date must be after start date')

class EarlyOutRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('DENIED', 'Denied'),
        ('REMOVED', 'Removed'),
    ]

    REASON_CHOICES = [
        ('REGULAR', 'Regular'),
        ('SICK', 'Sick'),
        ('FMLA', 'FMLA'),
        ('ADA', 'ADA'),
    ]

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='early_out_requests')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    reason = models.CharField(max_length=10, choices=REASON_CHOICES, default='REGULAR')
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    authorized_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='authorized_early_outs'
    )
    hours_worked = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    pit_number = models.CharField(max_length=10, null=True, blank=True)
    table_number = models.CharField(max_length=10, null=True, blank=True)
    toke_sign_off = models.ForeignKey(TokeSignOff, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.requested_at.date()}"

class Discrepancy(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('VERIFIED', 'Verified'),
        ('RESOLVED', 'Resolved'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reported_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reported_discrepancies'
    )
    description = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    reported_at = models.DateTimeField(auto_now_add=True)
    
    verified_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='verified_discrepancies'
    )
    verification_date = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(null=True, blank=True)
    
    resolved_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='resolved_discrepancies'
    )
    resolution_date = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-reported_at']
        verbose_name_plural = 'Discrepancies'

    def __str__(self):
        return f"Discrepancy {self.id} - {self.status}"

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=255)
    model_name = models.CharField(max_length=50, default='unknown')
    record_id = models.CharField(max_length=50, null=True, blank=True)
    changes = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    casino = models.CharField(max_length=100, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.get_full_name() if self.user else 'System'} - {self.action} {self.model_name} {self.record_id}"
