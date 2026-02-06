from django.contrib import admin
from .models import Scan


@admin.register(Scan)
class ScanAdmin(admin.ModelAdmin):
    list_display = ('id', 'url', 'site', 'status', 'score', 'pages_analyzed', 'created_at')
    list_filter = ('status', 'scan_type', 'created_at')
    search_fields = ('url', 'site__name')
    readonly_fields = ('created_at', 'started_at', 'completed_at')
