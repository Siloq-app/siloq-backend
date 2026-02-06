"""
Serializers for Site and APIKey models.
"""
from rest_framework import serializers
from .models import Site, APIKey


class SiteSerializer(serializers.ModelSerializer):
    """Serializer for Site model."""
    page_count = serializers.SerializerMethodField()
    api_key_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Site
        fields = (
            'id', 'name', 'url', 'wp_site_id', 'is_active',
            'last_synced_at', 'created_at', 'updated_at',
            'page_count', 'api_key_count'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'last_synced_at')

    def get_page_count(self, obj):
        """Get count of pages for this site."""
        return obj.pages.count()

    def get_api_key_count(self, obj):
        """Get count of active API keys for this site."""
        return obj.api_keys.filter(is_active=True).count()


class APIKeySerializer(serializers.ModelSerializer):
    """Serializer for APIKey model (safe - doesn't expose full key)."""
    
    class Meta:
        model = APIKey
        fields = (
            'id', 'site', 'name', 'key_prefix', 'is_active',
            'created_at', 'last_used_at', 'usage_count'
        )
        read_only_fields = ('id', 'site', 'key_prefix', 'created_at', 'last_used_at', 'usage_count')


class APIKeyCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating APIKey (includes full key in response)."""
    key = serializers.CharField(read_only=True, help_text="Full API key (shown only once)")
    
    class Meta:
        model = APIKey
        fields = ('id', 'name', 'key', 'key_prefix', 'created_at', 'is_active')
        read_only_fields = ('id', 'key', 'key_prefix', 'created_at', 'is_active')
