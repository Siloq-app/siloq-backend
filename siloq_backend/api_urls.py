"""
API URL routing for siloq_backend.
All API endpoints are prefixed with /api/v1/
"""
from django.urls import path, include
from integrations.views import verify_api_key
from siloq_backend.views import health_check

urlpatterns = [
    # Health check (no auth) - GET /api/v1/health/
    path('health/', health_check),
    # Dashboard authentication
    path('auth/', include('accounts.urls')),
    # WordPress plugin: POST /api/v1/auth/verify with Bearer <api_key>
    path('auth/verify', verify_api_key),
    # API key management
    path('api-keys/', include('sites.api_key_urls')),
    # Site management
    path('sites/', include('sites.urls')),
    # Page management
    path('pages/', include('seo.urls')),
    # WordPress integration endpoints (scans, page sync)
    path('', include('integrations.urls')),
]
