"""
Custom permissions for WordPress integrations.
"""
from rest_framework import permissions


class IsAPIKeyAuthenticated(permissions.BasePermission):
    """
    Permission to allow API key authenticated requests.
    """
    def has_permission(self, request, view):
        # Check if request was authenticated via API key
        if hasattr(request, 'auth') and isinstance(request.auth, dict):
            return request.auth.get('auth_type') == 'api_key'
        return False


class IsJWTOrAPIKeyAuthenticated(permissions.BasePermission):
    """
    Permission to allow either JWT (dashboard) or API key (WordPress) authentication.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
