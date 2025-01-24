from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.auth import get_user_model
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

class TokesViewSet(viewsets.ModelViewSet):
    serializer_class = TokesSerializer

    def get_queryset(self):
        return Tokes.objects.all().order_by('-date')

    @action(detail=False, methods=['get', 'post'])
    def current(self, request):
        """Get or create current toke."""
        today = timezone.now().date()
        current_toke = Tokes.objects.filter(date=today).first()
        
        if request.method == 'GET':
            if not current_toke:
                return Response(
                    {'error': 'No toke found for today'},
                    status=status.HTTP_404_NOT_FOUND
                )
            serializer = self.get_serializer(current_toke)
            return Response(serializer.data)
        
        # POST method - create if doesn't exist
        if current_toke:
            serializer = self.get_serializer(current_toke)
            return Response(serializer.data)
        
        current_toke = Tokes.objects.create(date=today)
        serializer = self.get_serializer(current_toke)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

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

class EarlyOutRequestViewSet(viewsets.ModelViewSet):
    queryset = EarlyOutRequest.objects.all()
    serializer_class = EarlyOutRequestSerializer

    @action(detail=False, methods=['get'])
    def current_list(self, request):
        """Get list of early out requests for today."""
        today = timezone.now().date()
        early_outs = self.queryset.filter(
            requested_at__date=today,
            status__in=['PENDING', 'APPROVED']
        ).order_by('requested_at')
        
        serializer = self.get_serializer(early_outs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def add_to_list(self, request):
        """Add user to early out list."""
        try:
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
            early_out = self.get_object()
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
        # Ensure the role is set to DEALER
        request.data['role'] = 'DEALER'
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
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

        dealer.is_active = True
        dealer.archived_by = None
        dealer.archived_at = None
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
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
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
