"""
URL routing for API keys.
"""
from rest_framework.routers import DefaultRouter
from .views import APIKeyViewSet

router = DefaultRouter()
router.register(r'', APIKeyViewSet, basename='apikey')

urlpatterns = router.urls
