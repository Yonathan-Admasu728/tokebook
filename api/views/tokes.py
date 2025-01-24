from datetime import datetime, timedelta
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..models import TokeSignOff, DealerVacation, EarlyOutRequest
from ..serializers import TokeSignOffSerializer

class TokeViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def current(self, request):
        """
        Get today's toke sign-offs including vacation and early-out information
        """
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
                        hours_worked="8.0",
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
                    'hours_worked': sign_off.hours_worked,
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
