"""
Page and SEO metrics models.
"""
from django.db import models
from sites.models import Site


class Page(models.Model):
    """
    Represents a WordPress page/post synced from WordPress.
    """
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='pages'
    )
    wp_post_id = models.IntegerField(
        help_text="WordPress post/page ID"
    )
    url = models.URLField()
    title = models.CharField(max_length=500)
    slug = models.SlugField(max_length=500)
    content = models.TextField(blank=True)
    excerpt = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        default='publish',
        choices=[
            ('publish', 'Published'),
            ('draft', 'Draft'),
            ('private', 'Private'),
        ]
    )
    published_at = models.DateTimeField(null=True, blank=True)
    modified_at = models.DateTimeField(null=True, blank=True)
    parent_id = models.IntegerField(null=True, blank=True)
    menu_order = models.IntegerField(default=0)
    
    # WordPress metadata
    yoast_title = models.CharField(max_length=500, blank=True)
    yoast_description = models.TextField(blank=True)
    featured_image = models.URLField(blank=True)
    
    # Siloq metadata
    siloq_page_id = models.CharField(max_length=255, blank=True, null=True)
    is_money_page = models.BooleanField(default=False, help_text="Designates this page as a money/target page")
    last_synced_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pages'
        ordering = ['-created_at']
        unique_together = [['site', 'wp_post_id']]
        indexes = [
            models.Index(fields=['site', 'status']),
            models.Index(fields=['url']),
        ]

    def __str__(self):
        return f"{self.title} ({self.site.name})"


class SEOData(models.Model):
    """
    SEO metrics and analysis data for a page.
    Stores comprehensive SEO information including titles, meta descriptions,
    headings, links, images, and identified issues.
    """
    page = models.OneToOneField(
        Page,
        on_delete=models.CASCADE,
        related_name='seo_data'
    )
    
    # Basic SEO elements
    meta_title = models.CharField(max_length=500, blank=True)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.CharField(max_length=500, blank=True)
    
    # Headings structure
    h1_count = models.IntegerField(default=0)
    h1_text = models.CharField(max_length=500, blank=True)
    h2_count = models.IntegerField(default=0)
    h2_texts = models.JSONField(
        default=list,
        help_text="List of H2 headings"
    )
    h3_count = models.IntegerField(default=0)
    h3_texts = models.JSONField(
        default=list,
        help_text="List of H3 headings"
    )
    
    # Links analysis
    internal_links_count = models.IntegerField(default=0)
    external_links_count = models.IntegerField(default=0)
    internal_links = models.JSONField(
        default=list,
        help_text="List of internal link URLs"
    )
    external_links = models.JSONField(
        default=list,
        help_text="List of external link URLs"
    )
    
    # Images analysis
    images_count = models.IntegerField(default=0)
    images_without_alt = models.IntegerField(default=0)
    images = models.JSONField(
        default=list,
        help_text="List of image URLs and alt texts"
    )
    
    # Content analysis
    word_count = models.IntegerField(default=0)
    reading_time_minutes = models.FloatField(default=0)
    
    # SEO Score and Issues
    seo_score = models.IntegerField(
        default=0,
        help_text="Overall SEO score (0-100)"
    )
    issues = models.JSONField(
        default=list,
        help_text="List of SEO issues found, e.g. [{'type': 'missing_meta_description', 'severity': 'high', 'message': '...'}]"
    )
    recommendations = models.JSONField(
        default=list,
        help_text="List of SEO recommendations"
    )
    
    # Technical SEO
    has_canonical = models.BooleanField(default=False)
    canonical_url = models.URLField(blank=True)
    has_schema = models.BooleanField(default=False)
    schema_type = models.CharField(max_length=100, blank=True)
    
    # Scan metadata
    scanned_at = models.DateTimeField(auto_now_add=True)
    scan_version = models.CharField(max_length=50, default='1.0')
    
    class Meta:
        db_table = 'seo_data'
        ordering = ['-scanned_at']

    def __str__(self):
        return f"SEO Data for {self.page.title}"
