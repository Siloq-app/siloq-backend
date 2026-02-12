"""
Custom authentication for API key-based requests from WordPress plugin.
Supports both Site Keys (sk_siloq_) and Account Keys (ak_siloq_).
"""
import logging
from urllib.parse import urlparse
from rest_framework import authentication, exceptions
from django.utils import timezone

logger = logging.getLogger(__name__)


class APIKeyAuthentication(authentication.BaseAuthentication):
    """
    Authenticate WordPress plugin requests using API keys.
    
    Supports two key types:
    - Site keys (sk_siloq_...): Tied to specific site
    - Account keys (ak_siloq_...): Master key, auto-creates sites
    
    API keys can be provided in:
    - Authorization header: "Bearer sk_siloq_xxx" or "Bearer ak_siloq_xxx"
    - X-API-Key header: "sk_siloq_xxx" or "ak_siloq_xxx"
    """
    
    def authenticate(self, request):
        api_key = self._extract_api_key(request)
        
        if not api_key:
            return None
        
        # Route to appropriate handler based on key prefix
        if api_key.startswith('ak_siloq_'):
            return self._authenticate_account_key(api_key, request)
        elif api_key.startswith('sk_siloq_'):
            return self._authenticate_site_key(api_key)
        else:
            logger.debug(f"API key has invalid prefix: {api_key[:10]}...")
            return None
    
    def _extract_api_key(self, request):
        """Extract API key from request headers."""
        api_key = None
        
        # Check Authorization header first
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            api_key = auth_header.split('Bearer ')[1].strip()
        
        # Fall back to X-API-Key header
        if not api_key:
            api_key = request.META.get('HTTP_X_API_KEY', '').strip()
        
        return api_key if api_key else None
    
    def _authenticate_site_key(self, api_key):
        """Authenticate using a site-specific key (sk_siloq_...)."""
        from sites.models import APIKey
        
        try:
            key_hash = APIKey.hash_key(api_key)
            api_key_obj = APIKey.objects.select_related('site', 'site__user').get(
                key_hash=key_hash,
                is_active=True
            )
            
            # Check expiration
            if api_key_obj.expires_at and api_key_obj.expires_at < timezone.now():
                raise exceptions.AuthenticationFailed('API key has expired')
            
            # Mark as used
            api_key_obj.mark_used()
            
            return (api_key_obj.site.user, {
                'api_key': api_key_obj,
                'site': api_key_obj.site,
                'auth_type': 'site_key'
            })
            
        except APIKey.DoesNotExist:
            logger.warning("Site API key not found in database")
            return None
        except Exception as e:
            logger.error(f"Site key authentication error: {str(e)}")
            return None
    
    def _authenticate_account_key(self, api_key, request):
        """
        Authenticate using an account-level key (ak_siloq_...).
        Auto-creates sites on sync if they don't exist.
        """
        from sites.models import AccountKey, Site
        
        try:
            key_hash = AccountKey.hash_key(api_key)
            account_key_obj = AccountKey.objects.select_related('user').get(
                key_hash=key_hash,
                is_active=True
            )
            
            # Check expiration
            if account_key_obj.expires_at and account_key_obj.expires_at < timezone.now():
                raise exceptions.AuthenticationFailed('Account key has expired')
            
            # Mark as used
            account_key_obj.mark_used()
            
            user = account_key_obj.user
            
            # Try to get or create site from request data
            site = self._get_or_create_site_for_account_key(user, account_key_obj, request)
            
            return (user, {
                'account_key': account_key_obj,
                'site': site,
                'auth_type': 'account_key',
                'auto_create_enabled': True
            })
            
        except AccountKey.DoesNotExist:
            logger.warning("Account API key not found in database")
            return None
        except Exception as e:
            logger.error(f"Account key authentication error: {str(e)}")
            return None
    
    def _get_or_create_site_for_account_key(self, user, account_key, request):
        """
        Get existing site or create new one for account key requests.
        Uses the 'url' field from request.data to identify/create the site.
        """
        from sites.models import Site
        
        # Try to get URL from request data
        site_url = None
        
        if hasattr(request, 'data') and request.data:
            site_url = request.data.get('url') or request.data.get('site_url')
        
        if not site_url:
            # Try to get from request body for POST requests
            try:
                import json
                body = request.body.decode('utf-8')
                if body:
                    data = json.loads(body)
                    site_url = data.get('url') or data.get('site_url')
            except:
                pass
        
        if not site_url:
            # No URL provided - return None, will be handled by the view
            logger.debug("No site URL in request for account key auth")
            return None
        
        # Normalize URL (remove trailing slash, ensure https)
        site_url = self._normalize_url(site_url)
        
        # Try to find existing site for this user
        try:
            site = Site.objects.get(user=user, url=site_url)
            logger.debug(f"Found existing site: {site.id} for URL: {site_url}")
            return site
        except Site.DoesNotExist:
            pass
        
        # Create new site
        site_name = self._extract_site_name(site_url)
        site = Site.objects.create(
            user=user,
            name=site_name,
            url=site_url,
            is_active=True
        )
        
        # Increment sites_created counter on account key
        account_key.increment_sites_created()
        
        logger.info(f"Auto-created site {site.id} ({site_name}) for account key {account_key.id}")
        
        return site
    
    def _normalize_url(self, url):
        """Normalize a URL for consistent matching."""
        if not url:
            return url
        
        # Add https if no scheme
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url
        
        # Parse and reconstruct
        parsed = urlparse(url)
        
        # Rebuild with just scheme and netloc (domain)
        normalized = f"{parsed.scheme}://{parsed.netloc}"
        
        # Remove trailing slash
        return normalized.rstrip('/')
    
    def _extract_site_name(self, url):
        """Extract a human-readable site name from URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            
            # Remove www prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Capitalize first letter of each word
            name = domain.replace('.', ' ').replace('-', ' ').title()
            
            # Remove common TLDs from name
            for tld in [' Com', ' Net', ' Org', ' Io', ' Ai', ' Co']:
                if name.endswith(tld):
                    name = name[:-len(tld)]
            
            return name.strip()
        except:
            return url
