from django.utils.deprecation import MiddlewareMixin
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from .models import AuditLog

class AuditLogMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.audit_data = {
            'ip_address': self.get_client_ip(request)
        }

    def process_response(self, request, response):
        # Skip audit logging for unauthenticated requests unless it's a login attempt
        if not hasattr(request, 'audit_log_action'):
            return response

        # For login attempts, we want to log even if authentication fails
        is_login_attempt = request.path.endswith('/auth/login/') and request.method == 'POST'
        
        # Only log if user is authenticated or it's a login attempt
        if request.user.is_authenticated or is_login_attempt:
            try:
                AuditLog.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    action=request.audit_log_action,
                    ip_address=request.audit_data.get('ip_address'),
                    content_type=getattr(request, 'audit_log_content_type', None),
                    object_id=getattr(request, 'audit_log_object_id', None),
                    details=getattr(request, 'audit_log_details', {}),
                    casino=request.user.casino if request.user.is_authenticated else None
                )
            except Exception as e:
                print(f"Error creating audit log: {str(e)}")
        
        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')

def log_action(action, content_object=None, details=None):
    def decorator(view_func):
        def wrapped_view(request, *args, **kwargs):
            request.audit_log_action = action
            if content_object:
                request.audit_log_content_type = ContentType.objects.get_for_model(content_object)
                request.audit_log_object_id = content_object.id
            
            # Handle details as a function or static value
            if callable(details):
                request.audit_log_details = details(request)
            else:
                request.audit_log_details = details or {}
                
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator
