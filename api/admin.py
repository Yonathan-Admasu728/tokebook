from django.contrib import admin
from .models import User, Casino, Tokes, TokeSignOff, EarlyOutRequest, Discrepancy, DealerVacation, AuditLog

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'employee_id', 'casino', 'has_pencil_flag')
    list_filter = ('role', 'has_pencil_flag')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'employee_id')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'employee_id')}),
        ('Role & Casino', {'fields': ('role', 'casino')}),
        ('Pencil Info', {'fields': ('has_pencil_flag',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

@admin.register(Casino)
class CasinoAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Tokes)
class TokesAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'finalized', 'per_hour_rate', 'created_at')
    list_filter = ('finalized', 'date')
    search_fields = ('id',)
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-date',)

@admin.register(TokeSignOff)
class TokeSignOffAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'toke', 'scheduled_hours', 'actual_hours', 'shift_start', 'shift_end', 'created_at')
    list_filter = ('created_at', 'toke__date')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('user', 'toke')

@admin.register(EarlyOutRequest)
class EarlyOutRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'reason', 'requested_at', 'processed_at', 'authorized_by')
    list_filter = ('status', 'reason', 'requested_at', 'processed_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'authorized_by__username')
    readonly_fields = ('requested_at', 'processed_at')
    raw_id_fields = ('user', 'authorized_by', 'toke_sign_off')

@admin.register(Discrepancy)
class DiscrepancyAdmin(admin.ModelAdmin):
    list_display = ('id', 'reported_by', 'status', 'reported_at', 'verified_by', 'resolved_by')
    list_filter = ('status', 'reported_at', 'verification_date', 'resolution_date')
    search_fields = (
        'reported_by__username',
        'verified_by__username',
        'resolved_by__username',
        'description',
        'resolution_notes'
    )
    readonly_fields = ('reported_at', 'verification_date', 'resolution_date')
    raw_id_fields = ('reported_by', 'verified_by', 'resolved_by')

@admin.register(DealerVacation)
class DealerVacationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'start_date', 'end_date', 'created_at')
    list_filter = ('start_date', 'end_date', 'created_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('user',)

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'action', 'model_name', 'record_id', 'timestamp')
    list_filter = ('action', 'model_name', 'timestamp')
    search_fields = ('user__username', 'model_name', 'record_id')
    readonly_fields = ('timestamp',)
    raw_id_fields = ('user',)
