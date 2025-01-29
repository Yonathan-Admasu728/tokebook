from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed

User = get_user_model()

class CustomJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        try:
            user_id = validated_token['sub']
            user = User.objects.get(id=user_id)
            print(f'JWT Auth - Found user: {user.username}')
            print(f'JWT Auth - User active status: {user.is_active}')
            if not user.is_active:
                print('JWT Auth - User is not active')
                raise AuthenticationFailed('User is not active')
            return user
        except User.DoesNotExist:
            print('JWT Auth - User not found')
            raise AuthenticationFailed('User not found')

class CustomModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = User.objects.get(username=username)
            print(f'CustomModelBackend - Found user: {user.username}')
            print(f'CustomModelBackend - User active status: {user.is_active}')
            print(f'CustomModelBackend - Checking password...')
            
            if user.check_password(password):
                print('CustomModelBackend - Password check passed')
                return user if self.user_can_authenticate(user) else None
            else:
                print('CustomModelBackend - Password check failed')
                return None
        except User.DoesNotExist:
            print('CustomModelBackend - User not found')
            return None

    def user_can_authenticate(self, user):
        can_auth = user.is_active
        print(f'CustomModelBackend - Can authenticate: {can_auth}')
        return can_auth
