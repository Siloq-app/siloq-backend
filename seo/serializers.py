"""
Serializers for SEO models.
"""
from rest_framework import serializers
from .models import (
    Page, SEOData, TopicCluster, CannibalizationIssue,
    CannibalizationIssuePage, ReverseSilo, ReverseSiloSupporting,
    PendingAction
)


class PageListSerializer(serializers.ModelSerializer):
    """Lightweight page serializer for lists."""
    class Meta:
        model = Page
        fields = ['id', 'title', 'url', 'slug', 'status']


class PageSerializer(serializers.ModelSerializer):
    """Full page serializer with SEO data."""
    class Meta:
        model = Page
        fields = [
            'id', 'wp_post_id', 'url', 'title', 'slug', 'content',
            'excerpt', 'status', 'published_at', 'modified_at',
            'yoast_title', 'yoast_description', 'featured_image',
            'last_synced_at', 'created_at'
        ]


class PageSyncSerializer(serializers.Serializer):
    """Serializer for WordPress page sync requests."""
    wp_post_id = serializers.IntegerField()
    url = serializers.URLField()
    title = serializers.CharField(max_length=500)
    slug = serializers.SlugField(max_length=500, required=False, allow_blank=True)
    content = serializers.CharField(required=False, allow_blank=True)
    excerpt = serializers.CharField(required=False, allow_blank=True)
    post_type = serializers.CharField(required=False)
    post_status = serializers.CharField(required=False)
    published_at = serializers.DateTimeField(required=False, allow_null=True)
    modified_at = serializers.DateTimeField(required=False, allow_null=True)


class SEODataSerializer(serializers.ModelSerializer):
    """Full SEO data serializer."""
    class Meta:
        model = SEOData
        exclude = ['page']


class TopicClusterSerializer(serializers.ModelSerializer):
    """Topic cluster serializer."""
    class Meta:
        model = TopicCluster
        fields = ['id', 'name', 'created_at']


# ============================================================
# Dashboard API Serializers
# ============================================================

class HealthSummarySerializer(serializers.Serializer):
    """
    Site health summary for dashboard.
    GET /sites/{id}/health-summary
    """
    health_score = serializers.IntegerField()
    health_score_delta = serializers.IntegerField(help_text="Change vs last week")
    cannibalization_count = serializers.IntegerField()
    silo_count = serializers.IntegerField()
    page_count = serializers.IntegerField()
    missing_links_count = serializers.IntegerField()
    last_scan_at = serializers.DateTimeField(allow_null=True)


class CompetingPageSerializer(serializers.ModelSerializer):
    """Page info for cannibalization issues."""
    impression_share = serializers.DecimalField(
        max_digits=5, decimal_places=2, 
        source='cannibalization_issues.first.impression_share',
        read_only=True
    )
    
    class Meta:
        model = Page
        fields = ['id', 'url', 'title', 'impression_share']


class CannibalizationIssueSerializer(serializers.ModelSerializer):
    """
    Cannibalization issue for dashboard.
    GET /sites/{id}/cannibalization-issues
    """
    competing_pages = serializers.SerializerMethodField()
    suggested_king = PageListSerializer(source='recommended_target_page', read_only=True)
    
    class Meta:
        model = CannibalizationIssue
        fields = [
            'id', 'keyword', 'severity', 'recommendation_type',
            'total_impressions', 'competing_pages', 'suggested_king',
            'created_at', 'updated_at'
        ]
    
    def get_competing_pages(self, obj):
        pages = []
        for cp in obj.competing_pages.select_related('page').order_by('order'):
            pages.append({
                'id': cp.page.id,
                'url': cp.page.url,
                'title': cp.page.title,
                'impression_share': float(cp.impression_share) if cp.impression_share else None
            })
        return pages


class CannibalizationIssueListSerializer(serializers.Serializer):
    """Response wrapper for cannibalization issues list."""
    issues = CannibalizationIssueSerializer(many=True)
    total = serializers.IntegerField()


class SupportingPageSerializer(serializers.ModelSerializer):
    """Supporting page in a silo."""
    is_linked = serializers.SerializerMethodField()
    
    class Meta:
        model = Page
        fields = ['id', 'url', 'title', 'status', 'is_linked']
    
    def get_is_linked(self, obj):
        return True


class ReverseSiloSerializer(serializers.ModelSerializer):
    """
    Reverse Silo for dashboard.
    GET /sites/{id}/silos
    """
    target_page = PageListSerializer(read_only=True)
    supporting_pages = serializers.SerializerMethodField()
    supporting_count = serializers.SerializerMethodField()
    linked_count = serializers.SerializerMethodField()
    topic_cluster = TopicClusterSerializer(read_only=True)
    
    class Meta:
        model = ReverseSilo
        fields = [
            'id', 'name', 'target_page', 'topic_cluster',
            'supporting_pages', 'supporting_count', 'linked_count',
            'created_at'
        ]
    
    def get_supporting_pages(self, obj):
        pages = []
        for sp in obj.supporting_pages.select_related('page').order_by('order'):
            pages.append({
                'id': sp.page.id,
                'url': sp.page.url,
                'title': sp.page.title,
                'status': sp.page.status,
                'order': sp.order
            })
        return pages
    
    def get_supporting_count(self, obj):
        return obj.supporting_pages.count()
    
    def get_linked_count(self, obj):
        return obj.supporting_pages.count()


class ReverseSiloListSerializer(serializers.Serializer):
    """Response wrapper for silos list."""
    silos = ReverseSiloSerializer(many=True)
    total = serializers.IntegerField()


class PendingActionSerializer(serializers.ModelSerializer):
    """
    Pending action for approval queue.
    GET /sites/{id}/pending-approvals
    """
    is_destructive = serializers.BooleanField(read_only=True)
    related_issue = CannibalizationIssueSerializer(read_only=True)
    
    class Meta:
        model = PendingAction
        fields = [
            'id', 'action_type', 'description', 'risk', 'status',
            'impact', 'doctrine', 'is_destructive',
            'related_issue', 'related_silo',
            'created_at', 'rollback_expires_at'
        ]


class PendingActionListSerializer(serializers.Serializer):
    """Response wrapper for pending actions."""
    pending_approvals = PendingActionSerializer(many=True)
    total = serializers.IntegerField()
