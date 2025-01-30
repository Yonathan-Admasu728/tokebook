from datetime import datetime, timedelta
from django.utils import timezone
from django.db import IntegrityError, models
from django.db.models import F
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..models import TokeSignOff, DealerVacation, EarlyOutRequest, Tokes
from ..serializers import TokeSignOffSerializer

class TokeViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

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
            if not all([hours is not None, shift_start, shift_end, shift_date]):
                return Response(
                    {'error': 'Missing required fields'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate hours
            try:
                hours = float(hours)
                if hours <= 0 or hours > 24:
                    return Response(
                        {'error': 'Hours must be between 0 and 24'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except (TypeError, ValueError):
                return Response(
                    {'error': 'Invalid hours format. Must be a number'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Parse shift_date string into date object
            try:
                shift_date_obj = datetime.strptime(shift_date, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Invalid shift date format. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate time formats
            try:
                datetime.strptime(shift_start, '%H:%M:%S')
                datetime.strptime(shift_end, '%H:%M:%S')
            except ValueError:
                return Response(
                    {'error': 'Invalid time format. Use HH:MM:SS'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get the toke and validate it exists
            try:
                toke = Tokes.objects.get(pk=pk)
            except Tokes.DoesNotExist:
                return Response(
                    {'error': 'Toke not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Validate shift_date matches toke date
            if shift_date_obj != toke.date:
                return Response(
                    {'error': 'Shift date must match toke date'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                # Create sign off
                sign_off = TokeSignOff.objects.create(
                    user=request.user,
                    toke=toke,  # Use toke object instead of toke_id
                    shift_date=shift_date_obj,
                    shift_start=shift_start,
                    shift_end=shift_end,
                    scheduled_hours=hours,  # Set scheduled hours
                    actual_hours=hours,     # Initially set actual hours to scheduled
                    original_hours=hours    # Store original hours
                )
            except IntegrityError:
                return Response(
                    {'error': 'You have already signed off for this toke period'},
                    status=status.HTTP_400_BAD_REQUEST
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

    @action(detail=True, methods=['post'])
    def finalize(self, request, pk=None):
        """Finalize a toke list and calculate per-hour rates."""
        try:
            toke = Tokes.objects.get(pk=pk)
            
            if toke.finalized:
                return Response(
                    {'error': 'Toke list is already finalized'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            if not toke.per_hour_rate:
                return Response(
                    {'error': 'Pool amount must be set before finalizing'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Calculate total hours and per-hour rate
            sign_offs = TokeSignOff.objects.filter(toke=toke)
            total_hours = sum(float(s.actual_hours) for s in sign_offs if s.actual_hours)
            
            if total_hours <= 0:
                return Response(
                    {'error': 'No valid hours found for toke distribution'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Set toke hours for each sign-off based on actual hours
            for sign_off in sign_offs:
                sign_off.toke_hours = sign_off.actual_hours
                sign_off.save()

            # Mark as finalized
            toke.finalized = True
            toke.save()

            return Response({'success': True})

        except Tokes.DoesNotExist:
            return Response(
                {'error': 'Toke not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['patch'])
    def update_pool(self, request, pk=None):
        """Update the pool amount for a toke list."""
        try:
            toke = Tokes.objects.get(pk=pk)
            
            if toke.finalized:
                return Response(
                    {'error': 'Cannot update pool amount for finalized toke list'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            pool_amount = request.data.get('total_pool_amount')
            if not pool_amount or float(pool_amount) <= 0:
                return Response(
                    {'error': 'Invalid pool amount'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Calculate per-hour rate
            sign_offs = TokeSignOff.objects.filter(toke=toke)
            total_hours = sum(float(s.actual_hours) for s in sign_offs if s.actual_hours)
            
            if total_hours <= 0:
                return Response(
                    {'error': 'No valid hours found for rate calculation'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            per_hour_rate = float(pool_amount) / total_hours
            toke.per_hour_rate = per_hour_rate
            toke.save()

            return Response({'success': True, 'per_hour_rate': per_hour_rate})

        except Tokes.DoesNotExist:
            return Response(
                {'error': 'Toke not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def previous_day(self, request):
        """Get previous day's toke list for distribution."""
        try:
            # Get yesterday's date in the casino's timezone
            yesterday = timezone.localtime().date() - timedelta(days=1)
            
            # Get or create yesterday's distribution toke list
            toke, created = Tokes.objects.get_or_create(
                date=yesterday,
                defaults={'is_collection_day': False}
            )
            
            # Get all sign-offs for yesterday
            sign_offs = TokeSignOff.objects.filter(
                toke=toke
            ).select_related('user')

            # Format response
            response_data = {
                'id': str(toke.id),
                'date': yesterday.isoformat(),
                'finalized': toke.finalized,
                'per_hour_rate': float(toke.per_hour_rate) if toke.per_hour_rate else None,
                'signOffs': [{
                    'id': str(sign_off.id),
                    'user': {
                        'id': str(sign_off.user.id),
                        'name': sign_off.user.get_full_name(),
                        'role': sign_off.user.role
                    },
                    'shift_start': sign_off.shift_start.strftime('%H:%M:%S') if sign_off.shift_start else None,
                    'shift_end': sign_off.shift_end.strftime('%H:%M:%S') if sign_off.shift_end else None,
                    'scheduled_hours': float(sign_off.scheduled_hours),
                    'actual_hours': float(sign_off.actual_hours) if sign_off.actual_hours else None,
                    'original_hours': float(sign_off.original_hours) if sign_off.original_hours else None,
                    'toke_amount': float(sign_off.toke_hours) if sign_off.toke_hours else None
                } for sign_off in sign_offs],
                'summary': {
                    'total_scheduled_hours': sum(float(s.scheduled_hours) for s in sign_offs),
                    'total_actual_hours': sum(float(s.actual_hours) for s in sign_offs if s.actual_hours),
                    'total_dealers': sign_offs.count(),
                    'early_outs': sign_offs.filter(actual_hours__lt=F('scheduled_hours')).count(),
                    'vacation_dealers': sign_offs.filter(actual_hours=8.0, shift_start__isnull=True).count()
                }
            }

            return Response(response_data)

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
            
            # Get or create today's collection toke list
            toke, created = Tokes.objects.get_or_create(
                date=today,
                defaults={'is_collection_day': True}
            )
            
            # Get all sign-offs for today
            sign_offs = TokeSignOff.objects.filter(
                toke=toke
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
                        toke=toke,
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
