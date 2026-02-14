"""
URL routing for Account (Master/Agency) API keys.
"""
from rest_framework.routers import DefaultRouter
from .api_keys import AccountKeyViewSet

router = DefaultRouter()
router.register(r'', AccountKeyViewSet, basename='accountkey')

urlpatterns = router.urls
