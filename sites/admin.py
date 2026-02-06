from django.contrib import admin
from .models import Site, APIKey


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'user', 'is_active', 'last_synced_at', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'url', 'user__email')
    readonly_fields = ('created_at', 'updated_at', 'last_synced_at')


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ('name', 'key_prefix', 'site', 'is_active', 'last_used_at', 'usage_count', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'key_prefix', 'site__name')
    readonly_fields = ('key_hash', 'key_prefix', 'created_at', 'last_used_at', 'usage_count', 'revoked_at')
