"""
API endpoints for the Keyword Assignment Registry.
"""
import logging

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from sites.models import Site
from seo.models import KeywordAssignment, Page
from seo.keyword_registry import (
    bootstrap_keyword_registry,
    check_keyword_available,
    assign_keyword,
    reassign_keyword,
    get_keyword_owner,
)

logger = logging.getLogger(__name__)


def _get_site_or_403(request, site_id):
    site = get_object_or_404(Site, id=site_id)
    if site.user != request.user:
        return None, Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    return site, None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def keyword_registry_list(request, site_id):
    """GET /api/v1/sites/{site_id}/keyword-registry/"""
    site, err = _get_site_or_403(request, site_id)
    if err:
        return err

    qs = KeywordAssignment.objects.filter(site=site).select_related('page', 'reassigned_from_page')

    # Optional filters
    status_filter = request.query_params.get('status')
    if status_filter:
        qs = qs.filter(status=status_filter)
    page_type = request.query_params.get('page_type')
    if page_type:
        qs = qs.filter(page_type=page_type)

    data = [
        {
            'id': ka.id,
            'keyword': ka.keyword,
            'page_id': ka.page_id,
            'page_title': ka.page.title,
            'page_url': ka.page.url,
            'silo_id': ka.silo_id,
            'page_type': ka.page_type,
            'assignment_source': ka.assignment_source,
            'status': ka.status,
            'assigned_at': ka.assigned_at,
            'updated_at': ka.updated_at,
            'reassigned_from_page_id': ka.reassigned_from_page_id,
            'reassigned_at': ka.reassigned_at,
        }
        for ka in qs
    ]

    return Response({'keyword_assignments': data, 'total': len(data)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def keyword_registry_bootstrap(request, site_id):
    """POST /api/v1/sites/{site_id}/keyword-registry/bootstrap/"""
    site, err = _get_site_or_403(request, site_id)
    if err:
        return err

    result = bootstrap_keyword_registry(site)
    return Response(result, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def keyword_registry_check(request, site_id):
    """POST /api/v1/sites/{site_id}/keyword-registry/check/"""
    site, err = _get_site_or_403(request, site_id)
    if err:
        return err

    keyword = request.data.get('keyword', '').strip()
    if not keyword:
        return Response({'error': 'keyword is required'}, status=status.HTTP_400_BAD_REQUEST)

    available = check_keyword_available(site, keyword)
    resp = {'keyword': keyword, 'available': available}

    if not available:
        owner = get_keyword_owner(site, keyword)
        if owner:
            resp['owner'] = {
                'page_id': owner.page_id,
                'page_title': owner.page.title,
                'page_url': owner.page.url,
            }

    return Response(resp)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def keyword_registry_assign(request, site_id):
    """POST /api/v1/sites/{site_id}/keyword-registry/assign/"""
    site, err = _get_site_or_403(request, site_id)
    if err:
        return err

    page_id = request.data.get('page_id')
    keyword = request.data.get('keyword', '').strip()
    silo_id = request.data.get('silo_id')
    page_type = request.data.get('page_type', 'general')

    if not page_id or not keyword:
        return Response({'error': 'page_id and keyword are required'}, status=status.HTTP_400_BAD_REQUEST)

    page = get_object_or_404(Page, id=page_id, site=site)

    try:
        ka = assign_keyword(site, page, keyword, silo_id=silo_id, page_type=page_type)
    except Exception as exc:
        # IntegrityError → keyword already taken
        owner = get_keyword_owner(site, keyword)
        conflict = {}
        if owner:
            conflict = {'page_id': owner.page_id, 'page_title': owner.page.title, 'page_url': owner.page.url}
        return Response(
            {'error': f'Keyword "{keyword}" is already assigned on this site.', 'conflict': conflict},
            status=status.HTTP_409_CONFLICT,
        )

    return Response({
        'id': ka.id,
        'keyword': ka.keyword,
        'page_id': ka.page_id,
        'status': ka.status,
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def keyword_registry_reassign(request, site_id):
    """POST /api/v1/sites/{site_id}/keyword-registry/reassign/"""
    site, err = _get_site_or_403(request, site_id)
    if err:
        return err

    keyword = request.data.get('keyword', '').strip()
    new_page_id = request.data.get('new_page_id')
    reason = request.data.get('reason', '')

    if not keyword or not new_page_id:
        return Response({'error': 'keyword and new_page_id are required'}, status=status.HTTP_400_BAD_REQUEST)

    new_page = get_object_or_404(Page, id=new_page_id, site=site)

    ka = reassign_keyword(site, keyword, new_page, reason=reason)

    return Response({
        'id': ka.id,
        'keyword': ka.keyword,
        'page_id': ka.page_id,
        'reassigned_from_page_id': ka.reassigned_from_page_id,
        'status': ka.status,
    }, status=status.HTTP_200_OK)
