from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import User, Casino, Tokes, TokeSignOff, EarlyOutRequest, Discrepancy, DealerVacation
from .serializers import (
    UserSerializer,
    CasinoSerializer,
    TokesSerializer,
    TokeSignOffSerializer,
    EarlyOutRequestSerializer,
    DiscrepancySerializer,
    VerificationSerializer,
    DealerVacationSerializer
)

class DealerVacationViewSet(viewsets.ModelViewSet):
    serializer_class = DealerVacationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            return DealerVacation.objects.all()
        return DealerVacation.objects.filter(dealer__casino=user.casino)

    def perform_create(self, serializer):
        serializer.save(approved_by=self.request.user)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]

class CasinoViewSet(viewsets.ModelViewSet):
    queryset = Casino.objects.all()
    serializer_class = CasinoSerializer
    permission_classes = [permissions.IsAuthenticated]

class TokesViewSet(viewsets.ModelViewSet):
    serializer_class = TokesSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            return Tokes.objects.all()
        return Tokes.objects.filter(casino=user.casino)

class TokeSignOffViewSet(viewsets.ModelViewSet):
    serializer_class = TokeSignOffSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            return TokeSignOff.objects.all()
        return TokeSignOff.objects.filter(toke__casino=user.casino)

class PencilViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['post'])
    def verify(self, request):
        """Verify a pencil ID and grant pencil access to the user"""
        user = request.user
        if user.role != 'SUPERVISOR':
            return Response(
                {'detail': 'Only supervisors can verify pencil IDs'},
                status=status.HTTP_403_FORBIDDEN
            )

        pencil_id = request.data.get('pencil_id')
        if not pencil_id:
            return Response(
                {'detail': 'Pencil ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Verify pencil ID matches user's stored pencil_id
            if not user.pencil_id or user.pencil_id != pencil_id:
                return Response(
                    {'detail': 'Invalid pencil ID'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if pencil is suspended
            if user.pencil_suspended_until and user.pencil_suspended_until > timezone.now():
                return Response(
                    {'detail': 'Your pencil access is currently suspended'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Update user's pencil flag
            user.has_pencil_flag = True
            user.save()
            return Response({'detail': 'Pencil access granted successfully'})
        except Exception as e:
            print(f"Error verifying pencil ID: {str(e)}")
            return Response(
                {'detail': 'Failed to verify pencil ID'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class EarlyOutRequestViewSet(viewsets.ModelViewSet):
    serializer_class = EarlyOutRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            return EarlyOutRequest.objects.all()
        return EarlyOutRequest.objects.filter(user__casino=user.casino)

    @action(detail=False, methods=['get'])
    def current_list(self, request):
        """Get list of early out requests for today based on user role"""
        try:
            today = timezone.now().date()
            user = request.user
            
            # Base queryset for today's requests
            early_outs = self.get_queryset().filter(
                requested_at__gte=timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time())),
                requested_at__lte=timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))
            ).select_related('user')
            
            # Filter based on include_approved parameter
            include_approved = request.query_params.get('include_approved') == 'true'
            if not include_approved:
                early_outs = early_outs.filter(status='PENDING')
            else:
                early_outs = early_outs.filter(status__in=['PENDING', 'APPROVED'])
            
            # Log initial query info
            print(f"User role: {user.role}")
            print(f"Initial query count: {early_outs.count()}")
            
            # Filter based on list type parameter
            list_type = request.query_params.get('list_type', 'dealer').upper()
            print(f"List type parameter: {list_type}")
            print(f"Raw list_type from request: {request.query_params.get('list_type')}")
            
            # Log all requests before filtering
            print("Before role filtering:")
            for req in early_outs:
                print(f"Request {req.id}: User={req.user.username}, Role={req.user.role}")
            
            # Ensure case-insensitive comparison for role filtering
            if list_type == 'SUPERVISOR':
                print("Filtering for supervisor requests")
                early_outs = early_outs.filter(user__role__iexact='SUPERVISOR')
            else:
                print("Filtering for dealer requests")
                early_outs = early_outs.filter(user__role__iexact='DEALER')
            
            # Log requests after filtering
            print("After role filtering:")
            for req in early_outs:
                print(f"Request {req.id}: User={req.user.username}, Role={req.user.role}")

            # Filter based on status if provided
            status = request.query_params.get('status')
            if status:
                early_outs = early_outs.filter(status=status)
            
            print(f"After role filtering count: {early_outs.count()}")
            
            # Log the requests being returned
            early_outs = early_outs.order_by('requested_at')
            for request in early_outs:
                print(f"Request: ID={request.id}, User={request.user.username}, Role={request.user.role}, "
                      f"Name={request.user.first_name} {request.user.last_name}, "
                      f"Pit={request.pit_number}, Status={request.status}")
            
            serializer = self.get_serializer(early_outs, many=True)
            data = serializer.data
            print(f"Serialized data: {data}")
            return Response(data)
        except Exception as e:
            print(f"Error fetching early out list: {str(e)}")
            return Response(
                {'detail': 'Failed to fetch early out list'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def add_to_list(self, request):
        user = request.user
        if user.role not in ['DEALER', 'SUPERVISOR']:
            return Response(
                {'detail': 'Only dealers and supervisors can add themselves to the early-out list'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if user already has a pending request from today
        today = timezone.now().date()
        existing_request = EarlyOutRequest.objects.filter(
            user=user,
            status='PENDING',
            requested_at__gte=timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time())),
            requested_at__lte=timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))
        ).first()
        
        if existing_request:
            return Response(
                {'detail': 'You already have an active early-out request'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get pit and table numbers from request
        pit_number = request.data.get('pit_number')
        table_number = request.data.get('table_number')
        
        # Validate pit number
        if not pit_number:
            return Response(
                {'detail': 'Pit number is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate table number for dealers only
        if user.role == 'DEALER' and not table_number:
            return Response(
                {'detail': 'Table number is required for dealers'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Create new request with user's name
            early_out = EarlyOutRequest.objects.create(
                user=user,
                status='PENDING',
                pit_number=pit_number,
                table_number=table_number if user.role == 'DEALER' else None,
                reason='REGULAR'
            )
            serializer = EarlyOutRequestSerializer(early_out)
            return Response(serializer.data)
        except Exception as e:
            print(f"Error creating early out request: {str(e)}")
            return Response(
                {'detail': 'Failed to create early out request'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def remove_from_list(self, request, pk=None):
        earlyout = self.get_object()
        
        # Check if user is trying to remove someone else's request
        if earlyout.user != request.user:
            return Response(
                {'detail': 'You can only remove your own early-out request'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check removal conditions and provide detailed feedback
        if not earlyout.can_remove(request.user):
            if earlyout.status == 'DENIED':
                return Response(
                    {'detail': 'Cannot remove a denied request'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            elif earlyout.status == 'APPROVED':
                if earlyout.toke_sign_off:
                    shift_date = earlyout.toke_sign_off.shift_date
                    shift_start = earlyout.toke_sign_off.shift_start
                    if shift_date and shift_start:
                        shift_datetime = timezone.make_aware(
                            timezone.datetime.combine(shift_date, shift_start)
                        )
                        if timezone.now() >= shift_datetime:
                            return Response(
                                {'detail': 'Cannot remove request after shift has started'},
                                status=status.HTTP_400_BAD_REQUEST
                            )
                return Response(
                    {'detail': 'Cannot remove this approved request'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                {'detail': 'Cannot remove this request in its current state'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Process removal
        earlyout.status = 'REMOVED'
        earlyout.processed_at = timezone.now()
        earlyout.save()
        
        return Response({
            'detail': 'Request successfully removed',
            'data': EarlyOutRequestSerializer(earlyout).data
        })

    @action(detail=True, methods=['post'])
    def authorize(self, request, pk=None):
        earlyout = self.get_object()
        
        # Check if user is trying to authorize their own request
        if earlyout.user == request.user:
            return Response(
                {'detail': 'You cannot authorize your own early-out request'},
                status=status.HTTP_403_FORBIDDEN
            )

        if not earlyout.can_authorize(request.user):
            return Response(
                {'detail': 'You do not have permission to authorize this request'},
                status=status.HTTP_403_FORBIDDEN
            )

        earlyout.status = 'APPROVED'
        earlyout.processed_at = timezone.now()
        earlyout.authorized_by = request.user
        earlyout.save()
        return Response(EarlyOutRequestSerializer(earlyout).data)

class DiscrepancyViewSet(viewsets.ModelViewSet):
    serializer_class = DiscrepancySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            return Discrepancy.objects.all()
        return Discrepancy.objects.filter(casino=user.casino)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def verify(self, request, pk=None):
        discrepancy = self.get_object()
        if not discrepancy.can_verify(request.user):
            return Response(
                {'detail': 'Only Toke Managers can verify discrepancies'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = VerificationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        discrepancy.status = data['status']
        discrepancy.verification_notes = data.get('verification_notes', '')
        discrepancy.verified_by = request.user
        discrepancy.verification_date = timezone.now()
        discrepancy.save()

        return Response(DiscrepancySerializer(discrepancy).data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def resolve(self, request, pk=None):
        discrepancy = self.get_object()
        if not discrepancy.can_resolve(request.user):
            return Response(
                {'detail': 'Only Casino Managers can resolve discrepancies'},
                status=status.HTTP_403_FORBIDDEN
            )

        discrepancy.status = 'RESOLVED'
        discrepancy.resolved_at = timezone.now()
        discrepancy.save()

        return Response(DiscrepancySerializer(discrepancy).data)
