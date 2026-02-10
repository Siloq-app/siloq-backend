"""
API URL routing for siloq_backend.
All API endpoints are prefixed with /api/v1/
"""
from django.urls import path, include
from integrations.views import verify_api_key

urlpatterns = [
    # Dashboard authentication
    path('auth/', include('accounts.urls')),
    # WordPress plugin: POST /api/v1/auth/verify with Bearer <api_key>
    path('auth/verify', verify_api_key),
    # API key management
    path('api-keys/', include('sites.api_key_urls')),
    # Site management
    path('sites/', include('sites.urls')),
    # WordPress integration endpoints (scans, page sync) - MUST come before seo.urls
    # so that /pages/sync/ is matched here, not by the seo router
    path('', include('integrations.urls')),
    # Page management (dashboard read-only)
    path('pages/', include('seo.urls')),
]
