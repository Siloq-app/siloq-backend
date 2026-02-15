"""
WordPress webhook integration for pushing content from Siloq API to WordPress sites.
"""
import json
import logging

import requests

logger = logging.getLogger(__name__)

WEBHOOK_TIMEOUT = 15  # seconds


def send_webhook_to_wordpress(site, event_type: str, data: dict) -> dict:
    """
    Send a webhook event to a WordPress site's Siloq plugin endpoint.

    Args:
        site: Site model instance (must have .url)
        event_type: e.g. 'content.create_draft'
        data: payload dict

    Returns:
        dict with 'success' (bool), 'status_code' (int|None), 'error' (str|None),
        and optionally 'response' (parsed JSON from WP).
    """
    url = f"{site.url.rstrip('/')}/wp-json/siloq/v1/webhook"

    payload = {
        'event_type': event_type,
        'site_id': str(site.id),
        'data': data,
    }

    body = json.dumps(payload)

    headers = {
        'Content-Type': 'application/json',
        'X-Siloq-Event': event_type,
        # HMAC signing deferred — WP plugin will verify via callback or
        # allowlist in a follow-up. For now send site_id so WP can confirm.
    }

    try:
        resp = requests.post(url, data=body, headers=headers, timeout=WEBHOOK_TIMEOUT)
        resp_data = None
        try:
            resp_data = resp.json()
        except Exception:
            pass

        if resp.status_code < 300:
            logger.info(
                "Webhook %s sent to %s — HTTP %s", event_type, url, resp.status_code
            )
            return {
                'success': True,
                'status_code': resp.status_code,
                'response': resp_data,
                'error': None,
            }
        else:
            logger.warning(
                "Webhook %s to %s failed — HTTP %s: %s",
                event_type, url, resp.status_code, resp.text[:500],
            )
            return {
                'success': False,
                'status_code': resp.status_code,
                'response': resp_data,
                'error': f"HTTP {resp.status_code}",
            }
    except requests.RequestException as exc:
        logger.error("Webhook %s to %s error: %s", event_type, url, exc)
        return {
            'success': False,
            'status_code': None,
            'response': None,
            'error': str(exc),
        }
