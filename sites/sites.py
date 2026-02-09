"""
Site management views.
Handles CRUD operations for sites, site overview, and dashboard endpoints.
"""
import logging
from datetime import timedelta

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Prefetch, Count, Q
from django.utils import timezone

from seo.models import (
    SEOData, Page, CannibalizationIssue, ReverseSilo, PendingAction
)
from seo.serializers import (
    HealthSummarySerializer, CannibalizationIssueSerializer,
    ReverseSiloSerializer, PendingActionSerializer
)
from .models import Site
from .serializers import SiteSerializer
from .permissions import IsSiteOwner

logger = logging.getLogger(__name__)


class SiteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing sites.
    
    list: GET /api/v1/sites/ - List all sites for current user
    create: POST /api/v1/sites/ - Create a new site
    retrieve: GET /api/v1/sites/{id}/ - Get site details
    update: PUT /api/v1/sites/{id}/ - Update site
    destroy: DELETE /api/v1/sites/{id}/ - Delete site
    
    Dashboard endpoints:
    health_summary: GET /api/v1/sites/{id}/health-summary/ - Dashboard health overview
    cannibalization_issues: GET /api/v1/sites/{id}/cannibalization-issues/ - List issues
    silos: GET /api/v1/sites/{id}/silos/ - List reverse silos
    pending_approvals: GET /api/v1/sites/{id}/pending-approvals/ - Approval queue
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
        (Legacy endpoint - use health-summary for dashboard)

        GET /api/v1/sites/{id}/overview/
        """
        site = self.get_object()
        pages = site.pages.prefetch_related(
            Prefetch('seo_data', queryset=SEOData.objects.all(), to_attr='prefetched_seo_data')
        )
        total_pages = pages.count()

        total_issues = 0
        for page in pages:
            seo_data_list = getattr(page, 'prefetched_seo_data', [])
            if seo_data_list and len(seo_data_list) > 0:
                seo_data = seo_data_list[0]
                if seo_data and seo_data.issues:
                    total_issues += len(seo_data.issues)

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

    # =========================================================
    # Dashboard API Endpoints
    # =========================================================

    @action(detail=True, methods=['get'], url_path='health-summary')
    def health_summary(self, request, pk=None):
        """
        Get comprehensive site health summary for dashboard.
        
        GET /api/v1/sites/{id}/health-summary/
        """
        site = self.get_object()
        
        page_count = site.pages.filter(status='publish').count()
        cannibalization_count = site.cannibalization_issues.count()
        silo_count = site.reverse_silos.count()
        
        pages = site.pages.prefetch_related('seo_data')
        total_issues = 0
        for page in pages:
            try:
                if page.seo_data and page.seo_data.issues:
                    total_issues += len(page.seo_data.issues)
            except SEOData.DoesNotExist:
                pass
        
        if page_count > 0:
            avg_issues = total_issues / page_count
            health_score = max(0, min(100, int(100 - (avg_issues * 10) - (cannibalization_count * 5))))
        else:
            health_score = 0
        
        health_score_delta = 0
        
        missing_links_count = 0
        for silo in site.reverse_silos.prefetch_related('supporting_pages'):
            missing_links_count += int(silo.supporting_pages.count() * 0.2)
        
        last_scan = site.pages.order_by('-last_synced_at').first()
        last_scan_at = last_scan.last_synced_at if last_scan else None
        
        return Response({
            'health_score': health_score,
            'health_score_delta': health_score_delta,
            'cannibalization_count': cannibalization_count,
            'silo_count': silo_count,
            'page_count': page_count,
            'missing_links_count': missing_links_count,
            'last_scan_at': last_scan_at,
        })

    @action(detail=True, methods=['get'], url_path='cannibalization-issues')
    def cannibalization_issues(self, request, pk=None):
        """
        Get all cannibalization issues for a site.
        
        GET /api/v1/sites/{id}/cannibalization-issues/
        """
        site = self.get_object()
        
        issues = site.cannibalization_issues.prefetch_related(
            'competing_pages__page',
            'recommended_target_page'
        ).order_by('-severity', '-total_impressions', '-created_at')
        
        serializer = CannibalizationIssueSerializer(issues, many=True)
        
        return Response({
            'issues': serializer.data,
            'total': issues.count()
        })

    @action(detail=True, methods=['get'])
    def silos(self, request, pk=None):
        """
        Get all reverse silos for a site.
        
        GET /api/v1/sites/{id}/silos/
        """
        site = self.get_object()
        
        silos = site.reverse_silos.select_related(
            'target_page', 'topic_cluster'
        ).prefetch_related(
            'supporting_pages__page'
        ).order_by('name')
        
        serializer = ReverseSiloSerializer(silos, many=True)
        
        return Response({
            'silos': serializer.data,
            'total': silos.count()
        })

    @action(detail=True, methods=['get'], url_path='pending-approvals')
    def pending_approvals(self, request, pk=None):
        """
        Get pending actions awaiting approval.
        
        GET /api/v1/sites/{id}/pending-approvals/
        """
        site = self.get_object()
        
        pending = site.pending_actions.filter(
            status='pending'
        ).select_related(
            'related_issue', 'related_silo'
        ).order_by('-risk', '-created_at')
        
        serializer = PendingActionSerializer(pending, many=True)
        
        return Response({
            'pending_approvals': serializer.data,
            'total': pending.count()
        })

    @action(detail=True, methods=['post'], url_path='approvals/(?P<action_id>[^/.]+)/approve')
    def approve_action(self, request, pk=None, action_id=None):
        """
        Approve a pending action.
        
        POST /api/v1/sites/{id}/approvals/{action_id}/approve/
        """
        site = self.get_object()
        pending_action = get_object_or_404(
            PendingAction, id=action_id, site=site, status='pending'
        )
        
        pending_action.status = 'approved'
        pending_action.save(update_fields=['status'])
        
        if pending_action.is_destructive:
            pending_action.rollback_expires_at = timezone.now() + timedelta(hours=48)
            pending_action.save(update_fields=['rollback_expires_at'])
        
        return Response({
            'message': 'Action approved',
            'action_id': pending_action.id,
            'status': pending_action.status
        })

    @action(detail=True, methods=['post'], url_path='approvals/(?P<action_id>[^/.]+)/deny')
    def deny_action(self, request, pk=None, action_id=None):
        """
        Deny a pending action.
        
        POST /api/v1/sites/{id}/approvals/{action_id}/deny/
        """
        site = self.get_object()
        pending_action = get_object_or_404(
            PendingAction, id=action_id, site=site, status='pending'
        )
        
        pending_action.status = 'denied'
        pending_action.save(update_fields=['status'])
        
        return Response({
            'message': 'Action denied',
            'action_id': pending_action.id,
            'status': pending_action.status
        })

    @action(detail=True, methods=['post'], url_path='approvals/(?P<action_id>[^/.]+)/rollback')
    def rollback_action(self, request, pk=None, action_id=None):
        """
        Rollback an executed action (within 48hr window).
        
        POST /api/v1/sites/{id}/approvals/{action_id}/rollback/
        """
        site = self.get_object()
        pending_action = get_object_or_404(
            PendingAction, id=action_id, site=site, status='executed'
        )
        
        if pending_action.rollback_expires_at and timezone.now() > pending_action.rollback_expires_at:
            return Response(
                {'error': 'Rollback window has expired'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not pending_action.rollback_data:
            return Response(
                {'error': 'No rollback data available'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        pending_action.status = 'rolled_back'
        pending_action.save(update_fields=['status'])
        
        return Response({
            'message': 'Action rolled back',
            'action_id': pending_action.id,
            'status': pending_action.status
        })
