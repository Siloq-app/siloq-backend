"""
URL routing for accounts app.
"""
from django.urls import path
from django.views.decorators.http import require_http_methods

# Lazy view imports to avoid AppRegistryNotReady
@require_http_methods(["POST"])
def login_view(request):
    from .auth import login
    return login(request)

@require_http_methods(["POST"])
def register_view(request):
    from .auth import register
    return register(request)

@require_http_methods(["POST"])
def logout_view(request):
    from .auth import logout
    return logout(request)

@require_http_methods(["GET"])
def me_view(request):
    from .auth import me
    return me(request)

@require_http_methods(["GET"])
def google_login_view(request):
    from .oauth import google_login
    return google_login(request)

@require_http_methods(["GET"])
def google_callback_view(request):
    from .oauth import google_callback
    return google_callback(request)

urlpatterns = [
    # Core authentication
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
    path('me/', me_view, name='me'),
    # Google OAuth
    path('google/login/', google_login_view, name='google_login'),
    path('google/callback/', google_callback_view, name='google_callback'),
]
