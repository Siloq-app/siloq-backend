"""
URL routing for sites app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .sites import SiteViewSet
from seo.content_recommendations import (
    get_content_recommendations,
    generate_from_recommendation,
    approve_content,
)
from seo.keyword_registry_views import (
    keyword_registry_list,
    keyword_registry_bootstrap,
    keyword_registry_check,
    keyword_registry_assign,
    keyword_registry_reassign,
)

router = DefaultRouter()
router.register(r'', SiteViewSet, basename='site')

urlpatterns = [
    path('', include(router.urls)),
    # Content Recommendations (nested under sites/{site_id}/)
    path('<int:site_id>/content-recommendations/', get_content_recommendations, name='site-content-recommendations'),
    path('<int:site_id>/content-recommendations/<str:rec_id>/generate/', generate_from_recommendation, name='site-content-recommendations-generate'),
    path('<int:site_id>/content/approve/', approve_content, name='site-content-approve'),
    # Keyword Registry
    path('<int:site_id>/keyword-registry/', keyword_registry_list, name='keyword-registry-list'),
    path('<int:site_id>/keyword-registry/bootstrap/', keyword_registry_bootstrap, name='keyword-registry-bootstrap'),
    path('<int:site_id>/keyword-registry/check/', keyword_registry_check, name='keyword-registry-check'),
    path('<int:site_id>/keyword-registry/assign/', keyword_registry_assign, name='keyword-registry-assign'),
    path('<int:site_id>/keyword-registry/reassign/', keyword_registry_reassign, name='keyword-registry-reassign'),
]
