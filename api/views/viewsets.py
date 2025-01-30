from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db import models
from ..models import TokeSignOff, Tokes, EarlyOutRequest, Casino, Discrepancy, DealerVacation, User
from ..serializers import (
    TokeSignOffSerializer,
    TokesSerializer,
    EarlyOutRequestSerializer,
    UserSerializer,
    CasinoSerializer,
    DiscrepancySerializer,
    DealerVacationSerializer
)

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class CasinoViewSet(viewsets.ModelViewSet):
    queryset = Casino.objects.all()
    serializer_class = CasinoSerializer

    @action(detail=False, methods=['get'])
    def shift_times(self, request):
        """Get shift times for a casino by name."""
        casino_name = request.query_params.get('name')
        if not casino_name:
            return Response(
                {'error': 'Casino name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            casino = Casino.objects.get(name=casino_name)
            return Response({
                'grave_start': casino.grave_start.strftime('%H:%M'),
                'grave_end': casino.grave_end.strftime('%H:%M'),
                'day_start': casino.day_start.strftime('%H:%M'),
                'day_end': casino.day_end.strftime('%H:%M'),
                'swing_start': casino.swing_start.strftime('%H:%M'),
                'swing_end': casino.swing_end.strftime('%H:%M'),
                'current_shift': casino.get_current_shift()
            })
        except Casino.DoesNotExist:
            return Response(
                {'error': f'Casino "{casino_name}" not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['patch'])
    def update_shift_times(self, request, pk=None):
        """Update shift times for a casino."""
        if request.user.role != 'ADMIN':
            return Response(
                {'error': 'Only admin users can modify shift times'},
                status=status.HTTP_403_FORBIDDEN
            )

        casino = self.get_object()
        serializer = self.get_serializer(casino, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

class TokesViewSet(viewsets.ModelViewSet):
    serializer_class = TokesSerializer

    def get_queryset(self):
        return Tokes.objects.all().order_by('-date')

    @action(detail=True, methods=['post'])
    def sign(self, request, pk=None):
        """Sign off for tokes with scheduled and actual hours."""
        try:
            # Get required fields
            hours = request.data.get('hours')
            shift_start = request.data.get('shift_start')
            shift_end = request.data.get('shift_end')
            shift_date = request.data.get('shift_date')

            # Validate input
            if not all([hours, shift_start, shift_end, shift_date]):
                return Response(
                    {'error': 'Missing required fields'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create sign off
            sign_off = TokeSignOff.objects.create(
                user=request.user,
                toke_id=pk,
                shift_date=shift_date,
                shift_start=shift_start,
                shift_end=shift_end,
                scheduled_hours=hours,  # Set scheduled hours
                actual_hours=hours,     # Initially set actual hours to scheduled
                original_hours=hours    # Store original hours
            )

            return Response({
                'success': True,
                'data': TokeSignOffSerializer(sign_off).data
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get', 'post'])
    def create_toke(self, request):
        """Create a new toke for today."""
        try:
            today = timezone.now().date()
            current_toke = Tokes.objects.filter(date=today).first()
            
            if current_toke:
                serializer = self.get_serializer(current_toke)
                return Response(serializer.data)
            
            current_toke = Tokes.objects.create(date=today)
            serializer = self.get_serializer(current_toke)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get today's toke sign-offs including vacation and early-out information."""
        try:
            # Get today's date in the casino's timezone
            today = timezone.localtime().date()
            
            # Get all sign-offs for today
            sign_offs = TokeSignOff.objects.filter(
                shift_date=today
            ).select_related('user')

            # Get all dealers on vacation today
            vacations = DealerVacation.objects.filter(
                start_date__lte=today,
                end_date__gte=today
            ).select_related('user')

            # Create vacation sign-offs
            vacation_sign_offs = []
            for vacation in vacations:
                # Skip if dealer already signed in
                if not sign_offs.filter(user=vacation.user).exists():
                    vacation_sign_offs.append(TokeSignOff(
                        user=vacation.user,
                        shift_date=today,
                        shift_start="00:00",
                        shift_end="00:00",
                        scheduled_hours=8.0,  # Default to 8 hours for vacation
                        actual_hours=8.0,     # Same for actual hours
                        original_hours=8.0,   # And original hours
                        is_on_vacation=True
                    ))

            # Get early-out requests for today's sign-offs
            early_outs = EarlyOutRequest.objects.filter(
                user__in=[s.user for s in sign_offs],
                requested_at__date=today,
                status__in=['PENDING', 'APPROVED']
            ).select_related('user')

            # Create early-out lookup
            early_out_lookup = {
                eo.user_id: {
                    'id': eo.id,
                    'status': eo.status,
                    'hours_worked': eo.hours_worked if eo.status == 'APPROVED' else None
                }
                for eo in early_outs
            }

            # Combine regular and vacation sign-offs
            all_sign_offs = list(sign_offs) + vacation_sign_offs

            # Format response
            response_data = {
                'id': str(today),
                'date': today.isoformat(),
                'signOffs': [{
                    'id': str(sign_off.id) if not getattr(sign_off, 'is_on_vacation', False) else f"v-{sign_off.user.id}",
                    'user': {
                        'id': str(sign_off.user.id),
                        'name': sign_off.user.get_full_name(),
                        'role': sign_off.user.role
                    },
                    'shift_start': sign_off.shift_start,
                    'shift_end': sign_off.shift_end,
                    'scheduled_hours': sign_off.scheduled_hours,
                    'actual_hours': sign_off.actual_hours,
                    'early_out': early_out_lookup.get(sign_off.user.id),
                    'is_on_vacation': getattr(sign_off, 'is_on_vacation', False)
                } for sign_off in all_sign_offs]
            }

            return Response(response_data)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def manage_current(self, request):
        """Get current toke for management."""
        today = timezone.now().date()
        current_toke = Tokes.objects.filter(date=today).first()
        
        if not current_toke:
            return Response(
                {'error': 'No toke found for today'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(current_toke)
        return Response(serializer.data)

class TokeSignOffViewSet(viewsets.ModelViewSet):
    queryset = TokeSignOff.objects.all()
    serializer_class = TokeSignOffSerializer

    @action(detail=True, methods=['post'])
    def update_hours(self, request, pk=None):
        """Update actual hours for a toke sign off."""
        try:
            # Validate user has pencil access
            if not request.user.has_pencil_flag:
                return Response(
                    {'error': 'Only users with pencil access can update hours'},
                    status=status.HTTP_403_FORBIDDEN
                )

            signoff = self.get_object()

            # Validate request body
            actual_hours = request.data.get('actual_hours')
            if actual_hours is None or not isinstance(actual_hours, (int, float)):
                return Response(
                    {'error': 'Actual hours is required and must be a number'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if actual_hours <= 0 or actual_hours > 24:
                return Response(
                    {'error': 'Hours must be between 0 and 24'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # If this is the first update, store original hours
            if not signoff.original_hours:
                signoff.original_hours = signoff.actual_hours

            # Update actual hours
            signoff.actual_hours = actual_hours
            signoff.save()

            serializer = self.get_serializer(signoff)
            return Response(serializer.data)

        except TokeSignOff.DoesNotExist:
            return Response(
                {'error': 'Toke sign off not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def last_shift(self, request):
        """Get the last shift's toke sign-off for the current user."""
        try:
            last_signoff = self.queryset.filter(
                user=request.user
            ).order_by('-shift_date').first()

            if not last_signoff:
                return Response(
                    {'error': 'No previous shifts found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            serializer = self.get_serializer(last_signoff)
            return Response(serializer.data)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

from rest_framework.permissions import IsAuthenticated
from ..authentication import CustomJWTAuthentication

class EarlyOutRequestViewSet(viewsets.ModelViewSet):
    queryset = EarlyOutRequest.objects.all()
    serializer_class = EarlyOutRequestSerializer
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def current_list(self, request):
        """Get list of early out requests for today."""
        print('EarlyOutRequestViewSet.current_list() called')
        print('User:', request.user)
        print('User role:', getattr(request.user, 'role', None))
        print('Auth header:', request.META.get('HTTP_AUTHORIZATION', 'No auth header'))
        print('Query params:', request.query_params)
        
        today = timezone.now().date()
        list_type = request.query_params.get('list_type', 'dealer')
        shift = request.query_params.get('shift')
        
        # Get requests for today
        queryset = EarlyOutRequest.objects.filter(
            requested_at__date=today
        ).exclude(status='REMOVED')

        # Filter by status if provided
        status = request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        else:
            # Default to only PENDING and APPROVED
            queryset = queryset.filter(status__in=['PENDING', 'APPROVED'])

        # Get the latest request for each user
        latest_requests = {}
        for req in queryset:
            user_id = req.user_id
            if user_id not in latest_requests or req.requested_at > latest_requests[user_id].requested_at:
                latest_requests[user_id] = req

        # Get the IDs of the latest requests
        latest_request_ids = [req.id for req in latest_requests.values()]

        # Filter to only include the latest request for each user
        queryset = queryset.filter(id__in=latest_request_ids)

        # Filter by shift if provided
        if shift:
            shift_mapping = {'day': 1, 'swing': 2, 'grave': 3}
            shift_number = shift_mapping.get(shift.lower())
            if shift_number:
                queryset = queryset.filter(user__shift=shift_number)
        
        # Filter based on user role
        if list_type == 'supervisor':
            queryset = queryset.filter(user__role='SUPERVISOR')
        else:  # dealer
            queryset = queryset.filter(user__role='DEALER')
            
        early_outs = queryset.order_by('requested_at')
        serializer = self.get_serializer(early_outs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def add_to_list(self, request):
        """Add user to early out list."""
        try:
            list_type = request.query_params.get('list_type', 'dealer')
            
            # Verify user role matches list type
            if list_type == 'supervisor' and request.user.role != 'SUPERVISOR':
                return Response(
                    {'error': 'Only supervisors can join the supervisor early out list'},
                    status=status.HTTP_403_FORBIDDEN
                )
            elif list_type == 'dealer' and request.user.role != 'DEALER':
                return Response(
                    {'error': 'Only dealers can join the dealer early out list'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            shift = request.query_params.get('shift')
            shift_mapping = {'day': 1, 'swing': 2, 'grave': 3}
            shift_number = shift_mapping.get(shift.lower()) if shift else None
            print(f"Comparing shifts - User shift: {request.user.shift}, Request shift: {shift_number}")
            if shift_number and request.user.shift != shift_number:
                return Response(
                    {'error': 'You can only join the early out list for your assigned shift'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Check for any active requests for today
            today = timezone.now().date()
            active_request = EarlyOutRequest.objects.filter(
                user=request.user,
                requested_at__date=today,
                status__in=['PENDING', 'APPROVED']
            ).order_by('-requested_at').first()

            if active_request:
                return Response(
                    {'error': 'Duplicate request', 'details': 'You already have an early out request for today'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create new request
            early_out = EarlyOutRequest.objects.create(
                user=request.user,
                pit_number=request.data.get('pit_number', ''),
                table_number=request.data.get('table_number'),
                status='PENDING'
            )
            serializer = self.get_serializer(early_out)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['delete'])
    def remove_from_list(self, request, pk=None):
        """Remove user from early out list."""
        try:
            list_type = request.query_params.get('list_type', 'dealer')
            early_out = self.get_object()
            
            # Verify user role matches list type
            if list_type == 'supervisor' and request.user.role != 'SUPERVISOR':
                return Response(
                    {'error': 'Only supervisors can remove from the supervisor early out list'},
                    status=status.HTTP_403_FORBIDDEN
                )
            elif list_type == 'dealer' and request.user.role != 'DEALER':
                return Response(
                    {'error': 'Only dealers can remove from the dealer early out list'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if early_out.user != request.user:
                return Response(
                    {'error': 'Not authorized to remove this request'},
                    status=status.HTTP_403_FORBIDDEN
                )
                
            early_out.status = 'REMOVED'
            early_out.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def authorize(self, request, pk=None):
        """Authorize an early out request."""
        try:
            # Only users with pencil_id or casino managers can authorize
            if not (request.user.pencil_id or request.user.role == 'CASINO_MANAGER'):
                return Response(
                    {'error': 'Pencil ID required to authorize early outs'},
                    status=status.HTTP_403_FORBIDDEN
                )

            early_out = self.get_object()
            
            # Validate request status
            if early_out.status != 'PENDING':
                return Response(
                    {'error': 'Only pending requests can be authorized'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get required fields
            hours_worked = request.data.get('hours_worked')
            pencil_id = request.data.get('pencil_id') or request.user.pencil_id
            toke_id = request.data.get('toke_id')

            if not hours_worked:
                return Response(
                    {'error': 'Hours worked is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # For dealers, require toke_id
            if early_out.user.role == 'DEALER' and not toke_id:
                return Response(
                    {'error': 'Toke ID is required for dealer early outs'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get the toke sign off for today
            today = timezone.now().date()
            toke_signoff = TokeSignOff.objects.filter(
                user=early_out.user,
                toke__date=today
            ).first()

            if not toke_signoff:
                return Response(
                    {'error': 'No toke sign off found for today'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Update early out request
            early_out.status = 'APPROVED'
            early_out.authorized_by = request.user
            early_out.authorized_by_name = f"{request.user.first_name} {request.user.last_name}"
            early_out.hours_worked = hours_worked
            early_out.processed_at = timezone.now()
            early_out.toke_sign_off = toke_signoff
            early_out.save()

            # Update toke sign off actual hours
            toke_signoff.actual_hours = hours_worked
            toke_signoff.save()

            # Return response with toke sign-off ID if it's a dealer
            response_data = {
                'id': early_out.id,
                'status': early_out.status,
                'authorized_by': early_out.authorized_by_name,
                'hours_worked': early_out.hours_worked,
                'processed_at': early_out.processed_at
            }

            if early_out.user.role == 'DEALER':
                response_data['toke_sign_off'] = toke_id

            return Response(response_data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class DiscrepancyViewSet(viewsets.ModelViewSet):
    queryset = Discrepancy.objects.all()
    serializer_class = DiscrepancySerializer

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify a discrepancy."""
        discrepancy = self.get_object()
        discrepancy.verified_by = request.user
        discrepancy.verification_date = timezone.now()
        discrepancy.status = 'VERIFIED'
        discrepancy.save()
        serializer = self.get_serializer(discrepancy)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve a discrepancy."""
        discrepancy = self.get_object()
        discrepancy.resolved_by = request.user
        discrepancy.resolution_date = timezone.now()
        discrepancy.resolution_notes = request.data.get('resolution_notes', '')
        discrepancy.status = 'RESOLVED'
        discrepancy.save()
        serializer = self.get_serializer(discrepancy)
        return Response(serializer.data)

from rest_framework.permissions import IsAuthenticated
from ..authentication import CustomJWTAuthentication

class DealerViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing dealers (users with DEALER role)
    """
    serializer_class = UserSerializer
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        print('DealerViewSet.get_queryset() called')
        print('User:', self.request.user)
        print('User role:', getattr(self.request.user, 'role', None))
        print('Auth header:', self.request.META.get('HTTP_AUTHORIZATION', 'No auth header'))
        print('Request method:', self.request.method)
        print('Request path:', self.request.path)
        
        # Check if user is authenticated
        if not self.request.user.is_authenticated:
            print('User is not authenticated')
            return User.objects.none()
        
        # Check user role
        if self.request.user.role in ['CASINO_MANAGER', 'TOKE_MANAGER']:
            print('User has correct role, returning dealers')
            return User.objects.filter(role='DEALER').order_by('first_name', 'last_name')
        
        print('User does not have correct role')
        return User.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })

    def create(self, request, *args, **kwargs):
        """Create a new dealer"""
        # Ensure required fields are set
        data = request.data.copy()
        data['role'] = 'DEALER'
        data['is_active'] = True
        data['username'] = data.get('employee_id')  # Set username to employee_id
        
        # Include password in initial data
        data['password'] = 'testpass123'
        
        # Create the user with all data including password
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def check_archived(self, request, pk=None):
        """Check if a dealer is archived by employee ID"""
        if request.user.role not in ['CASINO_MANAGER', 'TOKE_MANAGER']:
            return Response(
                {'error': 'Only casino managers and toke managers can check archived dealers'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            dealer = User.objects.get(employee_id=pk, role='DEALER', is_active=False)
            return Response({
                'success': True,
                'data': {
                    'id': dealer.id,
                    'archived_by': dealer.archived_by.id if dealer.archived_by else None,
                    'archived_at': dealer.archived_at.isoformat() if dealer.archived_at else None
                }
            })
        except User.DoesNotExist:
            return Response(
                {'error': 'No archived dealer found with this employee ID'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def reactivate(self, request, pk=None):
        """Reactivate an archived dealer"""
        if request.user.role not in ['CASINO_MANAGER', 'TOKE_MANAGER']:
            return Response(
                {'error': 'Only casino managers and toke managers can reactivate dealers'},
                status=status.HTTP_403_FORBIDDEN
            )

        dealer = self.get_object()
        if dealer.is_active:
            return Response(
                {'error': 'Dealer is already active'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update dealer data
        for field, value in request.data.items():
            if hasattr(dealer, field):
                setattr(dealer, field, value)

        # Update basic dealer data
        dealer.is_active = True
        dealer.archived_by = None
        dealer.archived_at = None
        dealer.username = dealer.employee_id  # Ensure username matches employee_id
        
        # Set password directly using set_password
        dealer.set_password('testpass123')
        dealer.save()

        serializer = self.get_serializer(dealer)
        return Response({
            'success': True,
            'data': serializer.data
        })

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive a dealer record before deletion"""
        if request.user.role not in ['CASINO_MANAGER', 'TOKE_MANAGER']:
            return Response(
                {'error': 'Only casino managers and toke managers can archive dealers'},
                status=status.HTTP_403_FORBIDDEN
            )

        dealer = self.get_object()
        
        # Create archive record
        dealer.archived_by = request.user
        dealer.archived_at = timezone.now()
        dealer.is_active = False
        dealer.save()

        return Response({
            'success': True,
            'data': {
                'id': dealer.id,
                'archived_by': request.user.id,
                'archived_at': dealer.archived_at.isoformat()
            }
        }, status=status.HTTP_200_OK)

class SupervisorViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in ['CASINO_MANAGER', 'TOKE_MANAGER']:
            return User.objects.filter(role='SUPERVISOR').order_by('first_name', 'last_name')
        return User.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })

    def create(self, request, *args, **kwargs):
        """Create a new supervisor"""
        data = request.data.copy()
        data['role'] = 'SUPERVISOR'  # Enforce role to SUPERVISOR
        data['is_active'] = True
        data['username'] = data.get('employee_id')  # Set username to employee_id
        
        # Include password in initial data
        data['password'] = 'testpass123'
        
        # Create the user with all data including password
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        """Update an existing supervisor"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data.copy()
        data['role'] = 'SUPERVISOR'  # Enforce role to SUPERVISOR
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({
            'success': True,
            'data': serializer.data
        })

    @action(detail=True, methods=['post'])
    def pencil(self, request, pk=None):
        """Grant pencil privileges to a supervisor"""
        if request.user.role != 'CASINO_MANAGER':
            return Response(
                {'error': 'Only casino managers can grant pencil privileges'},
                status=status.HTTP_403_FORBIDDEN
            )

        supervisor = self.get_object()
        if supervisor.role != 'SUPERVISOR':
            return Response(
                {'error': 'Pencil privileges can only be granted to supervisors'},
                status=status.HTTP_400_BAD_REQUEST
            )

        supervisor.has_pencil_flag = True
        supervisor.pencil_id = supervisor.employee_id
        supervisor.save()

        serializer = self.get_serializer(supervisor)
        return Response({
            'success': True,
            'data': serializer.data
        })

    @pencil.mapping.delete
    def remove_pencil(self, request, pk=None):
        """Remove pencil privileges from a supervisor"""
        if request.user.role != 'CASINO_MANAGER':
            return Response(
                {'error': 'Only casino managers can remove pencil privileges'},
                status=status.HTTP_403_FORBIDDEN
            )

        supervisor = self.get_object()
        if supervisor.role != 'SUPERVISOR':
            return Response(
                {'error': 'Pencil privileges can only be removed from supervisors'},
                status=status.HTTP_400_BAD_REQUEST
            )

        supervisor.has_pencil_flag = False
        supervisor.pencil_id = None
        supervisor.save()

        serializer = self.get_serializer(supervisor)
        return Response({
            'success': True,
            'data': serializer.data
        })

class DealerVacationViewSet(viewsets.ModelViewSet):
    queryset = DealerVacation.objects.all()
    serializer_class = DealerVacationSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role in ['CASINO_MANAGER', 'TOKE_MANAGER']:
            # Casino managers and toke managers can see all vacations
            queryset = self.queryset
        else:
            # Other users can only see their own vacations
            queryset = self.queryset.filter(user=user)
        
        # Filter by date range if provided
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(start_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(end_date__lte=end_date)
            
        return queryset.order_by('-start_date')

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a dealer vacation request."""
        if request.user.role not in ['CASINO_MANAGER', 'TOKE_MANAGER']:
            return Response(
                {'error': 'Only casino managers and toke managers can approve vacations'},
                status=status.HTTP_403_FORBIDDEN
            )

        vacation = self.get_object()
        if vacation.status != 'PENDING':
            return Response(
                {'error': 'Only pending vacation requests can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )

        vacation.approved_by = request.user
        vacation.approved_at = timezone.now()
        vacation.status = 'APPROVED'
        vacation.save()
        
        serializer = self.get_serializer(vacation)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def deny(self, request, pk=None):
        """Deny a dealer vacation request."""
        if request.user.role not in ['CASINO_MANAGER', 'TOKE_MANAGER']:
            return Response(
                {'error': 'Only casino managers and toke managers can deny vacations'},
                status=status.HTTP_403_FORBIDDEN
            )

        vacation = self.get_object()
        if vacation.status != 'PENDING':
            return Response(
                {'error': 'Only pending vacation requests can be denied'},
                status=status.HTTP_400_BAD_REQUEST
            )

        vacation.status = 'DENIED'
        vacation.save()
        
        serializer = self.get_serializer(vacation)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current dealer vacations."""
        list_type = request.query_params.get('list_type', 'all')
        today = timezone.now().date()
        
        queryset = self.queryset.filter(
            start_date__lte=today,
            end_date__gte=today,
            status='APPROVED'
        )
        
        if list_type == 'supervisor':
            queryset = queryset.filter(user__role='SUPERVISOR')
        elif list_type == 'dealer':
            queryset = queryset.filter(user__role='DEALER')
            
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def monthly_report(self, request):
        """Get vacation report for a specific month."""
        if request.user.role not in ['CASINO_MANAGER', 'TOKE_MANAGER']:
            return Response(
                {'error': 'Only casino managers and toke managers can access monthly reports'},
                status=status.HTTP_403_FORBIDDEN
            )

        month = request.query_params.get('month')
        year = request.query_params.get('year')

        if not month or not year:
            return Response(
                {'error': 'Month and year parameters are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            vacations = self.queryset.filter(
                start_date__year=year,
                start_date__month=month
            ).order_by('start_date')
            
            serializer = self.get_serializer(vacations, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get vacation history for the past 12 months."""
        if request.user.role not in ['CASINO_MANAGER', 'TOKE_MANAGER']:
            return Response(
                {'error': 'Only casino managers and toke managers can access vacation history'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Get current date
            today = timezone.now().date()
            
            # Calculate date 12 months ago
            twelve_months_ago = today - timezone.timedelta(days=365)
            
            # Get all approved vacations from the past 12 months
            vacations = self.queryset.filter(
                status='APPROVED',
                start_date__gte=twelve_months_ago,
                start_date__lte=today
            ).order_by('-start_date')  # Most recent first
            
            # Group vacations by month
            grouped_vacations = {}
            for vacation in vacations:
                month_key = vacation.start_date.strftime('%Y-%m')  # Format: YYYY-MM
                if month_key not in grouped_vacations:
                    grouped_vacations[month_key] = []
                grouped_vacations[month_key].append(self.get_serializer(vacation).data)
            
            return Response(grouped_vacations)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
