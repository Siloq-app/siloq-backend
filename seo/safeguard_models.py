"""
Minimal Django models for the content safeguards schema (v2).
These map to the tables in content-safeguards-db-schema.sql.
Full models will be expanded as other v2 modules come online.
"""
import uuid
from django.db import models


class SiloDefinition(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    site_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=255)
    slug = models.CharField(max_length=255)
    hub_page_url = models.CharField(max_length=2048, null=True, blank=True)
    hub_page_id = models.IntegerField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'silo_definitions'
        managed = False


class SiloKeyword(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    silo_id = models.UUIDField(db_index=True)
    site_id = models.UUIDField(db_index=True)
    keyword = models.CharField(max_length=500)
    keyword_type = models.CharField(max_length=20, default='supporting')
    search_volume = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'silo_keywords'
        managed = False


class PageMetadata(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    site_id = models.UUIDField(db_index=True)
    page_url = models.CharField(max_length=2048)
    page_id = models.IntegerField(null=True, blank=True)
    title_tag = models.CharField(max_length=500, null=True, blank=True)
    h1_tag = models.CharField(max_length=500, null=True, blank=True)
    canonical_url = models.CharField(max_length=2048, null=True, blank=True)
    is_indexable = models.BooleanField(default=True)
    silo_id = models.UUIDField(null=True, blank=True)
    url_depth = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'page_metadata'
        managed = False


class ValidationLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    site_id = models.UUIDField(db_index=True)
    proposed_title = models.CharField(max_length=500, null=True, blank=True)
    proposed_slug = models.CharField(max_length=500, null=True, blank=True)
    proposed_h1 = models.CharField(max_length=500, null=True, blank=True)
    proposed_keyword = models.CharField(max_length=500, null=True, blank=True)
    proposed_silo_id = models.UUIDField(null=True, blank=True)
    proposed_page_type = models.CharField(max_length=30, null=True, blank=True)
    overall_status = models.CharField(max_length=10)
    blocking_check = models.CharField(max_length=50, null=True, blank=True)
    check_results = models.JSONField(default=dict)
    user_action = models.CharField(max_length=30, null=True, blank=True)
    user_acknowledged_warnings = models.BooleanField(default=False)
    validation_source = models.CharField(max_length=30, default='generation')
    triggered_by = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'validation_log'
        managed = False
