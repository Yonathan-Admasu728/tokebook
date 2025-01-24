from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

class CustomJWTAuthentication(JWTAuthentication):
    def __init__(self):
        super().__init__()
        self._current_request = None

    def authenticate(self, request):
        """
        Authenticate the request and return a two-tuple of (user, token).
        """
        print("Starting authentication process")
        print("Request headers:", request.headers)
        print("Request META:", {k: v for k, v in request.META.items() if k.startswith('HTTP_')})
        
        # Store request for use in get_user
        self._current_request = request
        
        try:
            header = self.get_header(request)
            if header is None:
                print("No auth header found")
                return None

            raw_token = self.get_raw_token(header)
            if raw_token is None:
                print("No raw token found")
                return None

            print("Raw token found:", raw_token.decode('utf-8')[:20] + '...')
            validated_token = self.get_validated_token(raw_token)
            print("Token validated successfully")
            print("Token claims:", {
                'exp': validated_token.get('exp'),
                'iat': validated_token.get('iat'),
                'sub': validated_token.get('sub'),
                'user_id': validated_token.get('user_id'),
                'role': validated_token.get('role'),
                'token_type': validated_token.get('token_type')
            })

            user = self.get_user(validated_token)
            if user is None:
                print("No user found")
                return None

            print("User authenticated:", user)
            print("User role:", getattr(user, 'role', None))
            
            # Store user role in request
            request.user_role = user.role
            print("Stored user role in request:", request.user_role)
            
            return (user, validated_token)
            
        except Exception as e:
            print(f"Authentication error: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            if hasattr(e, '__dict__'):
                print(f"Error details: {e.__dict__}")
            raise

    def get_user(self, validated_token):
        """
        Attempts to find and return a user using the given validated token.
        """
        try:
            print("Getting user from token with claims:", validated_token)
            
            # Try 'sub' claim first (NextAuth style)
            user_id = validated_token.get('sub')
            if not user_id:
                # Fallback to 'user_id' claim (Django REST style)
                user_id = validated_token.get('user_id')
            
            if not user_id:
                print("No user ID found in token")
                raise InvalidToken('Token contained no recognizable user identification')

            print(f"Found user_id: {user_id}")
            user = self.user_model.objects.get(id=user_id)
            print(f"Found user: {user}, Active: {user.is_active}, Role: {user.role}")
            
            if not user.is_active:
                print("User is not active")
                raise InvalidToken('User is not active')
            
            return user
            
        except self.user_model.DoesNotExist:
            print(f"User with ID {user_id} not found")
            raise InvalidToken('User not found')
        except Exception as e:
            print(f"Error getting user: {str(e)}")
            raise
