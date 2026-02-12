"""
Intelligence Layer - Cannibalization Detection and Analysis

This module provides the core analysis logic for detecting keyword
cannibalization and generating content recommendations.

Cannibalization Types Detected:
1. URL Structure Cannibalization - Similar slugs, parent/child conflicts
2. Keyword Cannibalization - Same keywords in titles/content
3. Content Cannibalization - Same topic/intent overlap
4. Category vs Product Conflicts - Category pages competing with their products
5. Blog vs Money Page Conflicts - Informational content competing with commercial pages
"""
import re
from collections import defaultdict
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlparse
from django.db.models import Q
from django.utils import timezone


def extract_url_slug_keywords(url: str) -> List[str]:
    """
    Extract meaningful keywords from URL path/slug.
    
    Example: /products/blue-sapphire-engagement-ring/ 
    Returns: ['products', 'blue', 'sapphire', 'engagement', 'ring']
    """
    try:
        parsed = urlparse(url)
        path = parsed.path.strip('/')
    except:
        path = url.strip('/')
    
    # Split by / and - and _
    parts = re.split(r'[/\-_]', path.lower())
    
    # Filter out common non-meaningful parts
    stop_slugs = {
        'page', 'pages', 'post', 'posts', 'product', 'products', 
        'category', 'categories', 'tag', 'tags', 'shop', 'store',
        'blog', 'news', 'article', 'articles', 'index', 'home',
        'www', 'http', 'https', 'html', 'php', 'aspx', 'htm',
        '2019', '2020', '2021', '2022', '2023', '2024', '2025', '2026',
    }
    
    keywords = []
    for part in parts:
        part = part.strip()
        if part and len(part) > 2 and part not in stop_slugs and not part.isdigit():
            keywords.append(part)
    
    return keywords


def get_url_structure_type(url: str, post_type: str = None) -> str:
    """
    Classify URL by its structural type for conflict detection.
    
    Returns: 'category', 'product', 'blog', 'service', 'location', 'page', 'unknown'
    """
    path = urlparse(url).path.lower() if url else ''
    
    # Check post_type first if available
    if post_type:
        if post_type in ['product', 'product_cat']:
            return 'product' if post_type == 'product' else 'category'
        if post_type == 'post':
            return 'blog'
    
    # Infer from URL structure
    if any(x in path for x in ['/category/', '/categories/', '/product-category/', '/product_cat/']):
        return 'category'
    if any(x in path for x in ['/product/', '/products/', '/shop/', '/store/']):
        return 'product'
    if any(x in path for x in ['/blog/', '/news/', '/article/', '/post/', '/posts/']):
        return 'blog'
    if any(x in path for x in ['/service/', '/services/', '/solutions/']):
        return 'service'
    if any(x in path for x in ['/location/', '/locations/', '/areas/', '/cities/']):
        return 'location'
    
    return 'page'


def extract_keywords_from_content(content: str, title: str = '', meta_description: str = '') -> List[str]:
    """
    Extract potential target keywords from page content.
    
    Uses:
    1. Words from title (high weight)
    2. Words from meta description (medium weight)  
    3. H1 tags from content
    
    Returns list of keyword phrases.
    """
    keywords = []
    
    def clean_text(text: str) -> str:
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those',
        'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which', 'who',
        'when', 'where', 'why', 'how', 'all', 'each', 'every', 'both', 'few',
        'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only',
        'own', 'same', 'so', 'than', 'too', 'very', 'just', 'also', 'now',
        'your', 'our', 'their', 'its', 'my', 'his', 'her', 'about', 'into',
    }
    
    def extract_phrases(text: str, min_words: int = 1, max_words: int = 4) -> List[str]:
        """Extract meaningful phrases from text."""
        words = clean_text(text).split()
        words = [w for w in words if w not in stop_words and len(w) > 2]
        
        phrases = []
        # Single words
        for w in words:
            if len(w) > 3:
                phrases.append(w)
        
        # Multi-word phrases
        for n in range(2, max_words + 1):
            for i in range(len(words) - n + 1):
                phrase = ' '.join(words[i:i+n])
                phrases.append(phrase)
        
        return phrases
    
    # Extract from title (most important)
    if title:
        title_phrases = extract_phrases(title, 1, 4)
        keywords.extend(title_phrases)
    
    # Extract from meta description
    if meta_description:
        meta_phrases = extract_phrases(meta_description, 2, 4)
        keywords.extend(meta_phrases)
    
    # Extract from H1 if in content
    if content:
        h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', content, re.IGNORECASE | re.DOTALL)
        if h1_match:
            h1_text = re.sub(r'<[^>]+>', '', h1_match.group(1))  # Strip inner HTML
            h1_phrases = extract_phrases(h1_text, 1, 4)
            keywords.extend(h1_phrases)
    
    # Deduplicate
    seen = set()
    unique_keywords = []
    for kw in keywords:
        if kw not in seen and len(kw) > 3:
            seen.add(kw)
            unique_keywords.append(kw)
    
    return unique_keywords[:20]


def calculate_url_similarity(url1: str, url2: str) -> float:
    """
    Calculate similarity between two URLs based on slug keywords.
    Returns a score between 0 and 1.
    """
    kw1 = set(extract_url_slug_keywords(url1))
    kw2 = set(extract_url_slug_keywords(url2))
    
    if not kw1 or not kw2:
        return 0.0
    
    intersection = len(kw1 & kw2)
    union = len(kw1 | kw2)
    
    return intersection / union if union > 0 else 0.0


def calculate_keyword_similarity(kw1: str, kw2: str) -> float:
    """
    Calculate similarity between two keywords using word overlap.
    Returns a score between 0 and 1.
    """
    words1 = set(kw1.lower().split())
    words2 = set(kw2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    
    return intersection / union if union > 0 else 0.0


def detect_url_cannibalization(pages) -> List[Dict[str, Any]]:
    """
    Detect cannibalization based on URL structure patterns.
    
    Detects:
    1. Similar URL slugs targeting same keywords
    2. Category pages competing with their product pages
    3. Blog posts competing with service/product pages
    4. Multiple pages with nearly identical URL patterns
    """
    issues = []
    page_list = list(pages)
    
    # Build URL keyword index
    url_keywords = {}
    url_types = {}
    for page in page_list:
        url_keywords[page.id] = set(extract_url_slug_keywords(page.url or ''))
        url_types[page.id] = get_url_structure_type(
            page.url or '', 
            getattr(page, 'post_type', None)
        )
    
    # Group pages by shared URL keywords
    keyword_to_pages = defaultdict(list)
    for page in page_list:
        for kw in url_keywords.get(page.id, []):
            keyword_to_pages[kw].append(page)
    
    # Find URL-based conflicts
    processed_pairs = set()
    
    for kw, kw_pages in keyword_to_pages.items():
        if len(kw_pages) < 2:
            continue
        
        # Check pairs for conflicts
        for i, page_a in enumerate(kw_pages):
            for page_b in kw_pages[i+1:]:
                pair_key = tuple(sorted([page_a.id, page_b.id]))
                if pair_key in processed_pairs:
                    continue
                processed_pairs.add(pair_key)
                
                # Calculate URL similarity
                url_sim = calculate_url_similarity(page_a.url or '', page_b.url or '')
                
                if url_sim < 0.3:
                    continue  # Not similar enough
                
                type_a = url_types[page_a.id]
                type_b = url_types[page_b.id]
                
                # Determine conflict type and severity
                conflict_type = None
                severity = 'low'
                recommendation = 'review'
                
                # Category vs Product conflict (HIGH severity)
                if (type_a == 'category' and type_b == 'product') or \
                   (type_a == 'product' and type_b == 'category'):
                    conflict_type = 'category_product_conflict'
                    severity = 'high'
                    recommendation = 'differentiate'
                
                # Blog vs Service/Product conflict (HIGH severity)
                elif (type_a == 'blog' and type_b in ['service', 'product']) or \
                     (type_a in ['service', 'product'] and type_b == 'blog'):
                    conflict_type = 'blog_money_page_conflict'
                    severity = 'high'
                    recommendation = 'consolidate'
                
                # Two products with similar URLs (MEDIUM)
                elif type_a == 'product' and type_b == 'product' and url_sim > 0.5:
                    conflict_type = 'product_similarity'
                    severity = 'medium'
                    recommendation = 'differentiate'
                
                # Two blog posts with similar URLs (MEDIUM)
                elif type_a == 'blog' and type_b == 'blog' and url_sim > 0.5:
                    conflict_type = 'blog_overlap'
                    severity = 'medium'
                    recommendation = 'consolidate'
                
                # Generic similar URLs
                elif url_sim > 0.6:
                    conflict_type = 'url_similarity'
                    severity = 'medium'
                    recommendation = 'review'
                
                if conflict_type:
                    # Determine suggested king (prefer money page, then category, then higher traffic)
                    suggested_king = page_a
                    if type_b in ['product', 'service'] and type_a not in ['product', 'service']:
                        suggested_king = page_b
                    elif type_b == 'category' and type_a not in ['product', 'service', 'category']:
                        suggested_king = page_b
                    elif getattr(page_b, 'is_money_page', False) and not getattr(page_a, 'is_money_page', False):
                        suggested_king = page_b
                    
                    issues.append({
                        'type': 'url_structure',
                        'conflict_type': conflict_type,
                        'keyword': kw,
                        'severity': severity,
                        'recommendation_type': recommendation,
                        'url_similarity': round(url_sim, 2),
                        'competing_pages': [
                            {
                                'id': page_a.id,
                                'url': page_a.url,
                                'title': page_a.title,
                                'page_type': type_a,
                                'is_money_page': getattr(page_a, 'is_money_page', False),
                            },
                            {
                                'id': page_b.id,
                                'url': page_b.url,
                                'title': page_b.title,
                                'page_type': type_b,
                                'is_money_page': getattr(page_b, 'is_money_page', False),
                            }
                        ],
                        'suggested_king': {
                            'id': suggested_king.id,
                            'url': suggested_king.url,
                            'title': suggested_king.title,
                        },
                        'explanation': _get_conflict_explanation(conflict_type, type_a, type_b, kw),
                    })
    
    return issues


def _get_conflict_explanation(conflict_type: str, type_a: str, type_b: str, keyword: str) -> str:
    """Generate human-readable explanation for the conflict."""
    explanations = {
        'category_product_conflict': f"Category page and product page both contain '{keyword}' in URL. The category page may be competing with its own products for rankings.",
        'blog_money_page_conflict': f"Blog post and {type_a if type_a in ['product', 'service'] else type_b} page both target '{keyword}'. Blog posts can steal rankings from higher-converting pages.",
        'product_similarity': f"Multiple products have '{keyword}' in their URLs. Consider differentiating titles and descriptions to target distinct search intents.",
        'blog_overlap': f"Multiple blog posts target '{keyword}'. Consider consolidating into one comprehensive article.",
        'url_similarity': f"These pages have very similar URL structures around '{keyword}'. Review if they serve distinct user intents.",
    }
    return explanations.get(conflict_type, f"Pages compete for '{keyword}' based on URL structure.")


def detect_keyword_cannibalization(pages, include_noindex: bool = False) -> List[Dict[str, Any]]:
    """
    Detect keyword cannibalization based on title/content keywords.
    
    A cannibalization issue occurs when multiple pages target the same
    or very similar keywords, causing them to compete in search results.
    """
    keyword_pages = defaultdict(list)
    
    for page in pages:
        if not include_noindex and getattr(page, 'is_noindex', False):
            continue
            
        # Get keywords for this page
        try:
            seo_data = page.seo_data
        except Exception:
            seo_data = None
        
        meta_title = seo_data.meta_title if seo_data else ''
        meta_description = seo_data.meta_description if seo_data else ''
        
        keywords = extract_keywords_from_content(
            page.content or '',
            page.title or meta_title or '',
            meta_description or page.excerpt or ''
        )
        
        # Also extract from URL
        url_keywords = extract_url_slug_keywords(page.url or '')
        keywords.extend(url_keywords)
        
        for keyword in set(keywords):
            keyword_pages[keyword].append({
                'id': page.id,
                'url': page.url,
                'title': page.title,
                'is_money_page': getattr(page, 'is_money_page', False),
                'page_type': get_url_structure_type(page.url or '', getattr(page, 'post_type', None)),
            })
    
    # Find keywords with multiple competing pages
    issues = []
    processed_keywords = set()
    
    for keyword, page_list in keyword_pages.items():
        if len(page_list) < 2:
            continue
            
        # Skip if we've already processed a very similar keyword
        skip = False
        for processed in processed_keywords:
            if calculate_keyword_similarity(keyword, processed) > 0.8:
                skip = True
                break
        
        if skip:
            continue
            
        processed_keywords.add(keyword)
        
        # Calculate severity
        num_pages = len(page_list)
        has_money_page = any(p['is_money_page'] for p in page_list)
        has_blog = any(p['page_type'] == 'blog' for p in page_list)
        has_product = any(p['page_type'] in ['product', 'service'] for p in page_list)
        
        # Blog competing with product/service is HIGH severity
        if has_blog and has_product:
            severity = 'high'
        elif num_pages >= 3:
            severity = 'high'
        elif num_pages == 2 and has_money_page:
            severity = 'high'
        elif num_pages == 2:
            severity = 'medium'
        else:
            severity = 'low'
        
        # Find suggested king (prefer money page, then product/service, then first)
        suggested_king = None
        for p in page_list:
            if p['is_money_page']:
                suggested_king = p
                break
        if not suggested_king:
            for p in page_list:
                if p['page_type'] in ['product', 'service']:
                    suggested_king = p
                    break
        if not suggested_king:
            suggested_king = page_list[0]
        
        # Determine recommendation
        if num_pages >= 3 or (has_blog and len([p for p in page_list if p['page_type'] == 'blog']) > 1):
            recommendation = 'consolidate'
        elif has_blog and has_product:
            recommendation = 'redirect_or_differentiate'
        elif has_money_page:
            recommendation = 'differentiate'
        else:
            recommendation = 'consolidate'
        
        issues.append({
            'type': 'keyword',
            'keyword': keyword,
            'severity': severity,
            'recommendation_type': recommendation,
            'competing_pages': page_list,
            'suggested_king': suggested_king,
            'total_impressions': None,  # Would come from GSC
        })
    
    return issues


def detect_cannibalization(pages, include_noindex: bool = False) -> List[Dict[str, Any]]:
    """
    Comprehensive cannibalization detection combining URL and keyword analysis.
    
    Returns combined issues sorted by severity.
    """
    page_list = list(pages)
    
    if not page_list:
        return []
    
    # Run both detection methods
    url_issues = detect_url_cannibalization(page_list)
    keyword_issues = detect_keyword_cannibalization(pages, include_noindex)
    
    # Combine and deduplicate
    all_issues = []
    seen_page_pairs = set()
    
    # Add URL issues first (often higher signal)
    for issue in url_issues:
        page_ids = tuple(sorted([p['id'] for p in issue['competing_pages']]))
        if page_ids not in seen_page_pairs:
            seen_page_pairs.add(page_ids)
            all_issues.append(issue)
    
    # Add keyword issues that don't duplicate URL issues
    for issue in keyword_issues:
        page_ids = tuple(sorted([p['id'] for p in issue['competing_pages']]))
        if page_ids not in seen_page_pairs:
            seen_page_pairs.add(page_ids)
            all_issues.append(issue)
    
    # Sort by severity (high first) and number of competing pages
    severity_order = {'high': 0, 'medium': 1, 'low': 2}
    all_issues.sort(key=lambda x: (
        severity_order.get(x['severity'], 3), 
        -len(x['competing_pages'])
    ))
    
    return all_issues[:30]  # Return top 30 issues


def calculate_health_score(site) -> Dict[str, Any]:
    """
    Calculate overall site health score.
    
    Factors:
    - Cannibalization issues (-10 per high, -5 per medium, -2 per low)
    - Missing SEO data (-5 per page without)
    - Content organization bonus (+10 if silos exist)
    - Money pages defined bonus (+5)
    """
    pages = site.pages.all()
    total_pages = pages.count()
    
    if total_pages == 0:
        return {
            'health_score': 0,
            'health_score_delta': 0,
            'breakdown': {
                'base_score': 0,
                'cannibalization_penalty': 0,
                'seo_data_penalty': 0,
                'money_page_bonus': 0,
            }
        }
    
    # Start with base score of 75
    score = 75
    
    # Cannibalization penalties
    issues = detect_cannibalization(pages)
    cannibalization_penalty = 0
    for issue in issues:
        if issue['severity'] == 'high':
            cannibalization_penalty += 10
        elif issue['severity'] == 'medium':
            cannibalization_penalty += 5
        else:
            cannibalization_penalty += 2
    
    score -= min(cannibalization_penalty, 40)  # Cap penalty at 40
    
    # SEO data penalty
    pages_without_seo = 0
    for p in pages:
        try:
            _ = p.seo_data
        except Exception:
            pages_without_seo += 1
    seo_data_penalty = min((pages_without_seo / total_pages) * 20, 20) if total_pages > 0 else 0
    score -= seo_data_penalty
    
    # Money pages bonus
    money_pages = pages.filter(is_money_page=True).count()
    if money_pages > 0:
        score += 5
    
    # Ensure score is between 0 and 100
    score = max(0, min(100, score))
    
    return {
        'health_score': round(score),
        'health_score_delta': 0,
        'breakdown': {
            'base_score': 75,
            'cannibalization_penalty': -cannibalization_penalty,
            'seo_data_penalty': -round(seo_data_penalty),
            'money_page_bonus': 5 if money_pages > 0 else 0,
        }
    }


def generate_content_recommendations(pages, issues: List[Dict]) -> List[Dict[str, Any]]:
    """
    Generate content recommendations based on analysis.
    """
    recommendations = []
    page_list = list(pages)
    
    money_pages = [p for p in page_list if getattr(p, 'is_money_page', False)]
    
    # For each money page, suggest supporting content
    for mp in money_pages[:5]:
        recommendations.append({
            'type': 'supporting_content',
            'priority': 'high',
            'title': f'Create supporting content for "{mp.title}"',
            'description': f'Your money page needs supporting articles to build topical authority.',
            'action': 'generate',
            'target_page_id': mp.id,
            'target_page_url': mp.url,
        })
    
    # For cannibalization issues, suggest specific fixes
    for issue in issues[:10]:
        if issue.get('type') == 'url_structure':
            conflict_type = issue.get('conflict_type', '')
            
            if conflict_type == 'blog_money_page_conflict':
                recommendations.append({
                    'type': 'redirect',
                    'priority': 'high',
                    'title': f'Redirect blog post to money page for "{issue["keyword"]}"',
                    'description': 'Consider 301 redirecting the blog post to the product/service page to consolidate ranking power.',
                    'action': 'redirect',
                    'competing_pages': issue['competing_pages'],
                    'suggested_king': issue['suggested_king'],
                })
            elif conflict_type == 'category_product_conflict':
                recommendations.append({
                    'type': 'differentiation',
                    'priority': 'high',
                    'title': f'Differentiate category and product pages for "{issue["keyword"]}"',
                    'description': 'Update the category page to target broader terms and let products target specific variations.',
                    'action': 'edit',
                    'competing_pages': issue['competing_pages'],
                })
            elif conflict_type in ['blog_overlap', 'product_similarity']:
                recommendations.append({
                    'type': 'consolidation',
                    'priority': 'medium',
                    'title': f'Consolidate overlapping content for "{issue["keyword"]}"',
                    'description': f'{len(issue["competing_pages"])} pages are competing. Consider merging into one comprehensive page.',
                    'action': 'review',
                    'competing_pages': issue['competing_pages'],
                })
        
        elif issue.get('recommendation_type') == 'consolidate':
            recommendations.append({
                'type': 'consolidation',
                'priority': 'high' if issue['severity'] == 'high' else 'medium',
                'title': f'Consolidate pages targeting "{issue["keyword"]}"',
                'description': f'{len(issue["competing_pages"])} pages are competing for this keyword. Consider merging or differentiating.',
                'action': 'review',
                'competing_pages': issue['competing_pages'],
            })
    
    return recommendations[:15]


def analyze_site(site) -> Dict[str, Any]:
    """
    Run full analysis on a site.
    
    Returns comprehensive analysis including:
    - Health score
    - Cannibalization issues (URL + keyword based)
    - Content recommendations
    """
    pages = site.pages.all().prefetch_related('seo_data')
    
    # Calculate health score
    health = calculate_health_score(site)
    
    # Detect cannibalization (combined URL + keyword)
    issues = detect_cannibalization(pages)
    
    # Generate recommendations
    recommendations = generate_content_recommendations(pages, issues)
    
    # Count statistics
    page_list = list(pages)
    money_page_count = len([p for p in page_list if getattr(p, 'is_money_page', False)])
    total_pages = len(page_list)
    
    # Count by type
    url_issues = [i for i in issues if i.get('type') == 'url_structure']
    keyword_issues = [i for i in issues if i.get('type') == 'keyword']
    high_severity = len([i for i in issues if i['severity'] == 'high'])
    
    return {
        'site_id': site.id,
        'analyzed_at': timezone.now().isoformat(),
        'health_score': health['health_score'],
        'health_score_delta': health['health_score_delta'],
        'health_breakdown': health['breakdown'],
        'cannibalization_issues': issues,
        'cannibalization_count': len(issues),
        'url_structure_issues': len(url_issues),
        'keyword_issues': len(keyword_issues),
        'high_severity_count': high_severity,
        'recommendations': recommendations,
        'recommendation_count': len(recommendations),
        'page_count': total_pages,
        'money_page_count': money_page_count,
        'silo_count': 0,
        'missing_links_count': 0,
    }
