"""
SEO analysis views.
Handles retrieving SEO data for pages.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Page, SEOData
from .serializers import SEODataSerializer
from sites.models import Site


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_page_seo_data(request, page_id):
    """
    Get detailed SEO data for a specific page.
    
    GET /api/v1/pages/{page_id}/seo/
    """
    # Verify user owns the site containing this page
    user_sites = Site.objects.filter(user=request.user)
    page = get_object_or_404(Page, id=page_id, site__in=user_sites)
    
    seo_data = page.seo_data.first()
    
    if not seo_data:
        return Response(
            {'message': 'No SEO data available for this page'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = SEODataSerializer(seo_data)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_seo_data_by_site(request):
    """
    List all SEO data for a specific site.
    
    GET /api/v1/seo-data/?site_id={id}
    """
    site_id = request.query_params.get('site_id')
    if not site_id:
        return Response(
            {'error': 'site_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verify user owns the site
    site = get_object_or_404(Site, id=site_id, user=request.user)
    
    # Get all pages for this site with their SEO data
    pages = Page.objects.filter(site=site).select_related('seo_data')
    
    seo_data_list = []
    for page in pages:
        if hasattr(page, 'seo_data') and page.seo_data:
            serializer = SEODataSerializer(page.seo_data)
            data = serializer.data
            data['page_id'] = page.id
            data['page_title'] = page.title
            seo_data_list.append(data)
    
    return Response({
        'site_id': site.id,
        'site_name': site.name,
        'total_pages': pages.count(),
        'pages_with_seo_data': len(seo_data_list),
        'results': seo_data_list
    })
