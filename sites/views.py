"""
Views for Site and APIKey management.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Site, APIKey
from .serializers import SiteSerializer, APIKeySerializer, APIKeyCreateSerializer
from .permissions import IsSiteOwner, IsAPIKeyOwner


class SiteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing sites.
    
    list: GET /api/v1/sites/ - List all sites for current user
    create: POST /api/v1/sites/ - Create a new site
    retrieve: GET /api/v1/sites/{id}/ - Get site details
    update: PUT /api/v1/sites/{id}/ - Update site
    destroy: DELETE /api/v1/sites/{id}/ - Delete site
    overview: GET /api/v1/sites/{id}/overview/ - Get site overview (health score, stats)
    """
    serializer_class = SiteSerializer
    permission_classes = [IsAuthenticated, IsSiteOwner]

    def get_queryset(self):
        """Return only sites owned by the current user."""
        return Site.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Set the user when creating a site."""
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['get'])
    def overview(self, request, pk=None):
        """
        Get site overview with health score and aggregated stats.
        
        GET /api/v1/sites/{id}/overview/
        """
        site = self.get_object()
        
        # Calculate health score (simplified - can be enhanced)
        pages = site.pages.all()
        total_pages = pages.count()
        
        # Calculate SEO health score based on issues
        seo_data_list = [page.seo_data.first() for page in pages if page.seo_data.exists()]
        total_issues = sum(
            len(seo_data.issues) if seo_data and seo_data.issues else 0
            for seo_data in seo_data_list
        )
        
        # Simple health score calculation (0-100)
        # Lower issues = higher score
        if total_pages > 0:
            avg_issues_per_page = total_issues / total_pages
            health_score = max(0, min(100, 100 - (avg_issues_per_page * 10)))
        else:
            health_score = 0
        
        return Response({
            'site_id': site.id,
            'site_name': site.name,
            'health_score': round(health_score, 1),
            'total_pages': total_pages,
            'total_issues': total_issues,
            'last_synced_at': site.last_synced_at,
        })


class APIKeyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing API keys.
    
    list: GET /api/v1/api-keys/ - List all API keys for user's sites (optional ?site_id= for one site)
    create: POST /api/v1/api-keys/ - Create a new API key
    retrieve: GET /api/v1/api-keys/{id}/ - Get API key details
    destroy: DELETE /api/v1/api-keys/{id}/ - Revoke API key
    """
    permission_classes = [IsAuthenticated, IsAPIKeyOwner]

    def get_queryset(self):
        """Return API keys for sites owned by the current user; optional filter by site_id."""
        qs = APIKey.objects.filter(site__user=self.request.user)
        site_id = self.request.query_params.get('site_id')
        if site_id:
            qs = qs.filter(site_id=site_id)
        return qs

    def get_serializer_class(self):
        """Use different serializer for create vs list/retrieve."""
        if self.action == 'create':
            return APIKeyCreateSerializer
        return APIKeySerializer

    def create(self, request, *args, **kwargs):
        """
        Create a new API key for a specific site (site-wise tokens).
        Each site can have multiple keys; keys are scoped to one site.
        
        POST /api/v1/api-keys/
        Body: { "name": "Production Site Key", "site_id": 1 }
        """
        site_id = request.data.get('site_id')
        if not site_id:
            return Response(
                {'error': 'site_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify user owns the site
        site = get_object_or_404(Site, id=site_id, user=request.user)
        
        # Generate API key
        full_key, key_prefix, key_hash = APIKey.generate_key()
        
        # Create API key record
        api_key = APIKey.objects.create(
            site=site,
            name=request.data.get('name', 'Unnamed Key'),
            key_hash=key_hash,
            key_prefix=key_prefix,
        )
        
        serializer = APIKeyCreateSerializer(api_key)
        # Add the full key to response (only shown once)
        response_data = serializer.data
        response_data['key'] = full_key
        
        return Response({
            'message': 'API key created successfully',
            'key': response_data
        }, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """
        Revoke an API key.
        
        DELETE /api/v1/api-keys/{id}/
        """
        api_key = self.get_object()
        api_key.revoke()
        return Response(
            {'message': 'API key revoked successfully'},
            status=status.HTTP_200_OK
        )
