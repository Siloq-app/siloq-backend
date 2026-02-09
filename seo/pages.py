"""
Page management views.
Handles listing and retrieving pages with SEO data.
"""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Page
from .serializers import PageSerializer, PageListSerializer
from sites.models import Site


class PageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing pages (read-only for dashboard).
    
    list: GET /api/v1/pages/ - List pages (filtered by site_id)
    retrieve: GET /api/v1/pages/{id}/ - Get page details with SEO data
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return pages for sites owned by the current user."""
        user_sites = Site.objects.filter(user=self.request.user)
        queryset = Page.objects.filter(site__in=user_sites)

        # Filter by site_id if provided
        site_id = self.request.query_params.get('site_id')
        if site_id:
            queryset = queryset.filter(site_id=site_id)

        # Prefetch related seo_data for list efficiency (OneToOne relation)
        return queryset.select_related('site', 'seo_data')

    def get_serializer_class(self):
        """Use lightweight serializer for list, full serializer for detail."""
        if self.action == 'list':
            return PageListSerializer
        return PageSerializer
