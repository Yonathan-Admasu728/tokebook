from rest_framework import serializers
from django.contrib.auth.hashers import make_password
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

    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'password', 'first_name', 'last_name', 'email',
            'employee_id', 'role', 'has_pencil_flag', 'pencil_id', 'casino', 'casino_name',
            'name', 'shift', 'shift_label'
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        # Create user instance but don't save yet
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        
        # Set password and save
        if password:
            user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        # Handle password separately
        password = validated_data.pop('password', None)
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            
        # Set password if provided
        if password:
            instance.set_password(password)
            
        instance.save()
        return instance

class CasinoSerializer(serializers.ModelSerializer):
    current_shift = serializers.CharField(source='get_current_shift', read_only=True)
    
    class Meta:
        model = Casino
        fields = [
            'id', 'name', 
            'grave_start', 'grave_end',
            'day_start', 'day_end',
            'swing_start', 'swing_end',
            'current_shift',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, data):
        """
        Validate that shift times make sense and cover 24 hours
        """
        if 'day_start' in data and 'day_end' in data:
            if data['day_start'] >= data['day_end']:
                raise serializers.ValidationError({
                    'day_end': 'Day shift end time must be after start time'
                })

        # Note: We don't validate swing and grave shifts the same way
        # because they can cross midnight

        return data

class TokesSerializer(serializers.ModelSerializer):
    signOffs = serializers.SerializerMethodField()
    date = serializers.DateField(format='%Y-%m-%d')

    class Meta:
        model = Tokes
        fields = [
            'id', 'date', 'finalized', 'per_hour_rate',
            'created_at', 'updated_at', 'signOffs'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_signOffs(self, obj):
        sign_offs = TokeSignOff.objects.filter(toke=obj).select_related('user')
        return TokeSignOffSerializer(sign_offs, many=True).data

class EarlyOutRequestSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    authorized_by_name = serializers.CharField(source='authorized_by.get_full_name', read_only=True)

    class Meta:
        model = EarlyOutRequest
        fields = [
            'id', 'user', 'user_name', 'pit_number', 'table_number',
            'requested_at', 'status', 'reason', 'authorized_by',
            'authorized_by_name', 'hours_worked'
        ]
        read_only_fields = ['id', 'user', 'requested_at', 'authorized_by']

class TokeSignOffSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    early_out = serializers.SerializerMethodField()
    is_on_vacation = serializers.BooleanField(default=False)
    signed_at = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S')

    class Meta:
        model = TokeSignOff
        fields = [
            'id', 'user', 'shift_date', 'shift_start', 'shift_end',
            'scheduled_hours', 'actual_hours', 'original_hours',
            'toke_hours', 'early_out', 'is_on_vacation',
            'created_at', 'updated_at', 'signed_at'
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
