"""
Custom permissions for sites app.
"""
from rest_framework import permissions


class IsSiteOwner(permissions.BasePermission):
    """
    Permission to check if user owns the site.
    """
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class IsAPIKeyOwner(permissions.BasePermission):
    """
    Permission to check if user owns the site that the API key belongs to.
    """
    def has_object_permission(self, request, view, obj):
        return obj.site.user == request.user
