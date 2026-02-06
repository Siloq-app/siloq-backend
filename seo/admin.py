from django.contrib import admin
from .models import Page, SEOData


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ('title', 'site', 'url', 'status', 'last_synced_at', 'created_at')
    list_filter = ('status', 'site', 'created_at')
    search_fields = ('title', 'url', 'site__name')
    readonly_fields = ('created_at', 'updated_at', 'last_synced_at')


@admin.register(SEOData)
class SEODataAdmin(admin.ModelAdmin):
    list_display = ('page', 'seo_score', 'h1_count', 'word_count', 'scanned_at')
    list_filter = ('scanned_at', 'has_schema', 'has_canonical')
    search_fields = ('page__title', 'page__url')
    readonly_fields = ('scanned_at',)
