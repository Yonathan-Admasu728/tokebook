from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.views.decorators.csrf import csrf_exempt
from .views import viewsets
from .views.auth import login, signup, reset_password

router = DefaultRouter()
router.register(r'users', viewsets.UserViewSet)
router.register(r'dealers', viewsets.DealerViewSet, basename='dealers')
router.register(r'casinos', viewsets.CasinoViewSet)
router.register(r'tokes', viewsets.TokesViewSet, basename='tokes')
router.register(r'toke-signoffs', viewsets.TokeSignOffViewSet, basename='toke-sign-offs')
router.register(r'discrepancies', viewsets.DiscrepancyViewSet, basename='discrepancies')
router.register(r'dealer-vacations', viewsets.DealerVacationViewSet, basename='dealer-vacations')
router.register(r'supervisors', viewsets.SupervisorViewSet, basename='supervisors')
router.register(r'early-out-requests', viewsets.EarlyOutRequestViewSet, basename='early-out-requests')

urlpatterns = [
    # Auth URLs
    path('auth/login/', csrf_exempt(login), name='login'),
    path('auth/signup/', csrf_exempt(signup), name='signup'),
    path('auth/reset-password/', csrf_exempt(reset_password), name='reset_password'),

    # Core functionality routes
    path('tokes/current/', csrf_exempt(viewsets.TokesViewSet.as_view({'get': 'current', 'post': 'create_toke'})), name='current_toke'),
    path('tokes/manage/current/', csrf_exempt(viewsets.TokesViewSet.as_view({'get': 'manage_current'})), name='manage_current_toke'),
    path('toke-signoffs/<uuid:pk>/update-hours/', csrf_exempt(viewsets.TokeSignOffViewSet.as_view({'post': 'update_hours'})), name='update_toke_hours'),
    path('tokes/<uuid:pk>/sign/', csrf_exempt(viewsets.TokesViewSet.as_view({'post': 'sign'})), name='sign_toke'),
    path('toke-signoffs/last_shift/', csrf_exempt(viewsets.TokeSignOffViewSet.as_view({'get': 'last_shift'})), name='last_shift'),

    # Discrepancy URLs
    path('discrepancies/<uuid:pk>/verify/', csrf_exempt(viewsets.DiscrepancyViewSet.as_view({'post': 'verify'})), name='discrepancy-verify'),
    path('discrepancies/<uuid:pk>/resolve/', csrf_exempt(viewsets.DiscrepancyViewSet.as_view({'post': 'resolve'})), name='discrepancy-resolve'),

    # Dealer Vacation URLs
    path('dealer-vacations/<uuid:pk>/approve/', csrf_exempt(viewsets.DealerVacationViewSet.as_view({'post': 'approve'})), name='dealer-vacation-approve'),
    path('dealer-vacations/<uuid:pk>/deny/', csrf_exempt(viewsets.DealerVacationViewSet.as_view({'post': 'deny'})), name='dealer-vacation-deny'),
    path('dealer-vacations/monthly-report/', csrf_exempt(viewsets.DealerVacationViewSet.as_view({'get': 'monthly_report'})), name='dealer-vacation-monthly-report'),
    path('dealer-vacations/current/', csrf_exempt(viewsets.DealerVacationViewSet.as_view({'get': 'current'})), name='dealer-vacation-current'),

    # Early Out Request URLs
    path('early-out-requests/current-list/', csrf_exempt(viewsets.EarlyOutRequestViewSet.as_view({'get': 'current_list'})), name='early-out-request-current-list'),
    path('early-out-requests/add-to-list/', csrf_exempt(viewsets.EarlyOutRequestViewSet.as_view({'post': 'add_to_list'})), name='early-out-request-add'),
    path('early-out-requests/<int:pk>/remove-from-list/', csrf_exempt(viewsets.EarlyOutRequestViewSet.as_view({'delete': 'remove_from_list'})), name='early-out-request-remove'),
    path('early-out-requests/<int:pk>/authorize/', csrf_exempt(viewsets.EarlyOutRequestViewSet.as_view({'post': 'authorize'})), name='early-out-request-authorize'),

    # Router URLs
    path('', include(router.urls)),
]
