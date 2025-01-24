from rest_framework import serializers
from .models import User, Casino, Tokes, TokeSignOff, DealerVacation, EarlyOutRequest, Discrepancy

class UserSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=True, allow_blank=False)
    last_name = serializers.CharField(required=True, allow_blank=False)
    casino_name = serializers.CharField(source='casino.name', read_only=True)
    name = serializers.SerializerMethodField()
    shift_label = serializers.SerializerMethodField()

    def get_name(self, obj):
        # Always return the full name for the user
        return f"{obj.first_name} {obj.last_name}".strip()

    def get_shift_label(self, obj):
        shift_labels = {1: 'Day', 2: 'Swing', 3: 'Grave'}
        return shift_labels.get(obj.shift, 'Unknown')

    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'email',
            'employee_id', 'role', 'has_pencil_flag', 'pencil_id', 'casino', 'casino_name',
            'name', 'shift', 'shift_label'
        ]
        read_only_fields = ['id']

class CasinoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Casino
        fields = ['id', 'name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class TokesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tokes
        fields = [
            'id', 'date', 'finalized', 'per_hour_rate',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class EarlyOutRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = EarlyOutRequest
        fields = ['id', 'status', 'hours_worked']
        read_only_fields = ['id']

class TokeSignOffSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    early_out = serializers.SerializerMethodField()
    is_on_vacation = serializers.BooleanField(default=False)

    class Meta:
        model = TokeSignOff
        fields = [
            'id', 'user', 'shift_date', 'shift_start', 'shift_end',
            'hours_worked', 'early_out', 'is_on_vacation',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_early_out(self, obj):
        # Get today's early out request for this user if it exists
        early_out = EarlyOutRequest.objects.filter(
            user=obj.user,
            requested_at__date=obj.shift_date,
            status__in=['PENDING', 'APPROVED']
        ).first()

        if early_out:
            serializer = EarlyOutRequestSerializer(early_out)
            return serializer.data
        return None

class DealerVacationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    approved_by = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        source='user',
        queryset=User.objects.filter(role='DEALER'),
        write_only=True
    )

    class Meta:
        model = DealerVacation
        fields = [
            'id', 'user', 'user_id', 'start_date', 'end_date',
            'status', 'notes', 'approved_by', 'approved_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'approved_by', 'approved_at',
            'created_at', 'updated_at'
        ]

    def validate(self, data):
        if data.get('end_date') and data.get('start_date'):
            if data['end_date'] < data['start_date']:
                raise serializers.ValidationError({
                    'end_date': 'End date must be after start date'
                })
        return data

class DiscrepancySerializer(serializers.ModelSerializer):
    reported_by = UserSerializer(read_only=True)
    verified_by = UserSerializer(read_only=True)
    resolved_by = UserSerializer(read_only=True)

    class Meta:
        model = Discrepancy
        fields = [
            'id', 'reported_by', 'description', 'status',
            'reported_at', 'verified_by', 'verification_date',
            'verification_notes', 'resolved_by', 'resolution_date',
            'resolution_notes'
        ]
        read_only_fields = [
            'id', 'reported_at', 'verification_date',
            'resolution_date'
        ]
