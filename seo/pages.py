"""
Page management views.
Handles listing and retrieving pages with SEO data.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Page
from .serializers import PageSerializer, PageListSerializer
from sites.models import Site


class LargeResultsSetPagination(PageNumberPagination):
    """Allow up to 1000 pages per request for dashboard views."""
    page_size = 1000
    page_size_query_param = 'page_size'
    max_page_size = 5000


class PageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing pages (read-only for dashboard).
    
    list: GET /api/v1/pages/ - List pages (filtered by site_id)
    retrieve: GET /api/v1/pages/{id}/ - Get page details with SEO data
    """
    permission_classes = [IsAuthenticated]
    pagination_class = LargeResultsSetPagination

    def get_queryset(self):
        """Return pages for sites owned by the current user."""
        user_sites = Site.objects.filter(user=self.request.user)
        queryset = Page.objects.filter(site__in=user_sites)
        
        # Filter out noindex pages by default
        include_noindex = self.request.query_params.get('include_noindex', 'false').lower()
        if include_noindex != 'true':
            queryset = queryset.filter(is_noindex=False)

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

    @action(detail=True, methods=['post'])
    def toggle_money_page(self, request, pk=None):
        """
        Toggle the is_money_page status for a page.
        POST /api/v1/pages/{id}/toggle_money_page/
        """
        try:
            # Get the page, ensuring it belongs to the user's sites
            user_sites = Site.objects.filter(user=request.user)
            page = Page.objects.get(pk=pk, site__in=user_sites)
            
            # Toggle the field
            page.is_money_page = not page.is_money_page
            page.save(update_fields=['is_money_page'])
            
            return Response({
                'success': True,
                'id': page.id,
                'is_money_page': page.is_money_page,
                'message': f'Page "{page.title}" is now {"a money page" if page.is_money_page else "a regular page"}.'
            }, status=status.HTTP_200_OK)
            
        except Page.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Page not found or you do not have permission to modify it.'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
