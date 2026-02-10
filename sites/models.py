"""
Site and API Key models.
"""
import secrets
import hashlib
from django.db import models
from django.conf import settings
from django.utils import timezone


class Site(models.Model):
    """
    Represents a WordPress website connected to Siloq.
    One user can have multiple sites.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sites'
    )
    name = models.CharField(max_length=255)
    url = models.URLField(help_text="Base URL of the WordPress site")
    wp_site_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="WordPress site identifier"
    )
    is_active = models.BooleanField(default=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    sync_requested_at = models.DateTimeField(null=True, blank=True, help_text="When user requested a sync from dashboard")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sites'
        ordering = ['-created_at']
        unique_together = [['user', 'url']]

    def __str__(self):
        return f"{self.name} ({self.url})"


class APIKey(models.Model):
    """
    API Key for authenticating WordPress plugin requests.
    Keys are hashed before storage and prefixed with 'sk_siloq_'.
    """
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='api_keys'
    )
    name = models.CharField(
        max_length=255,
        help_text="Human-readable name for the API key"
    )
    key_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="SHA-256 hash of the API key"
    )
    key_prefix = models.CharField(
        max_length=20,
        help_text="First 16 characters of the key for display"
    )
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    usage_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'api_keys'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.key_prefix}...)"

    @staticmethod
    def generate_key():
        """
        Generate a new API key.
        Returns: (full_key, prefix, hash)
        """
        prefix = 'sk_siloq'
        random_part = secrets.token_urlsafe(32)
        full_key = f"{prefix}_{random_part}"
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        key_prefix = full_key[:16] + '...'
        
        return full_key, key_prefix, key_hash

    @staticmethod
    def hash_key(key):
        """Hash an API key for comparison."""
        return hashlib.sha256(key.encode()).hexdigest()

    def verify_key(self, key):
        """Verify if a provided key matches this API key."""
        return self.key_hash == self.hash_key(key) and self.is_active

    def revoke(self):
        """Revoke this API key."""
        self.is_active = False
        self.revoked_at = timezone.now()
        self.save()

    def mark_used(self):
        """Mark this key as used (update last_used_at and increment usage_count)."""
        self.last_used_at = timezone.now()
        self.usage_count += 1
        self.save(update_fields=['last_used_at', 'usage_count'])
