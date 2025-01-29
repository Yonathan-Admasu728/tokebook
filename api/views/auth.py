from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from datetime import timedelta
from ..serializers import UserSerializer
from ..middleware import log_action

User = get_user_model()

@api_view(['POST'])
@permission_classes([AllowAny])
@log_action('login_attempt', details=lambda request: {
    'username': request.data.get('username'),
    'success': False  # Will be updated in the view if login succeeds
})
def login(request):
    """Handle user login and return tokens."""
    print('Login request data:', request.data)
    username = request.data.get('username')
    password = request.data.get('password')

    print(f'Login attempt for username: {username}')
    if not username or not password:
        return Response(
            {'error': 'Both username and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    print(f'Attempting to authenticate user with username: {username}')
    try:
        existing_user = User.objects.get(username=username)
        print(f'Found user in database: {existing_user.username}, active: {existing_user.is_active}')
        print(f'Stored password hash: {existing_user.password}')
    except User.DoesNotExist:
        print(f'No user found with username: {username}')
        existing_user = None

    from api.authentication import CustomModelBackend
    auth_backend = CustomModelBackend()
    user = auth_backend.authenticate(request, username=username, password=password)
    print(f'Authentication result for {username}:', 'Success' if user else 'Failed')
    if not user and existing_user:
        print('User exists but authentication failed - password mismatch')
    if not user:
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    print(f'Creating tokens for user {username}')

    # Update audit log details to indicate successful login
    request.audit_log_details['success'] = True

    # Create refresh token
    refresh = RefreshToken.for_user(user)
    
    # Add custom claims to both refresh and access tokens
    for token in [refresh, refresh.access_token]:
        # Essential claims for authentication
        token['sub'] = str(user.id)  # Primary user identifier
        token['token_type'] = 'refresh' if token == refresh else 'access'
        token['jti'] = str(token['jti'])  # Ensure JTI is a string
        
        # User data claims
        token['role'] = user.role
        token['casino'] = user.casino
        token['name'] = f"{user.first_name} {user.last_name}".strip()
        token['has_pencil_flag'] = user.has_pencil_flag
        token['email'] = user.email
        if hasattr(user, 'pencil_id'):
            token['pencil_id'] = user.pencil_id
        
        # Set token timestamps
        now = timezone.now()
        token['iat'] = int(now.timestamp())
        token['exp'] = int((now + timedelta(days=30)).timestamp())  # 30 days expiry

    serializer = UserSerializer(user)

    response_data = {
        'user': serializer.data,
        'tokens': {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
    }
    print('Login response data:', response_data)
    print('Access token:', str(refresh.access_token))
    return Response(response_data)

@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    """Handle user registration."""
    serializer = UserSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check if user already exists
    username = serializer.validated_data.get('username')
    email = serializer.validated_data.get('email')
    if User.objects.filter(username=username).exists():
        return Response(
            {'error': 'Username already exists'},
            status=status.HTTP_400_BAD_REQUEST
        )
    if email and User.objects.filter(email=email).exists():
        return Response(
            {'error': 'Email already exists'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Create user
    password = request.data.get('password')
    if not password:
        return Response(
            {'error': 'Password is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = serializer.save()
    user.set_password(password)
    user.save()

    # Generate tokens
    refresh = RefreshToken.for_user(user)

    return Response({
        'user': serializer.data,
        'tokens': {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
    }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    """Handle password reset."""
    email = request.data.get('email')
    if not email:
        return Response(
            {'error': 'Email is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # Don't reveal if user exists
        return Response({
            'message': 'If an account exists with this email, a password reset link will be sent.'
        })

    # TODO: Implement actual password reset logic
    # For now, just return success message
    return Response({
        'message': 'If an account exists with this email, a password reset link will be sent.'
    })
