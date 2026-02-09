"""
Stripe billing views for Siloq.
Handles checkout sessions, webhooks, and subscription management.
"""
import json
import stripe
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

stripe.api_key = settings.STRIPE_SECRET_KEY

# Price IDs for each tier
PRICE_IDS = {
    'pro': settings.STRIPE_PRICE_PRO,
    'builder': settings.STRIPE_PRICE_BUILDER,
    'architect': settings.STRIPE_PRICE_ARCHITECT,
    'empire': settings.STRIPE_PRICE_EMPIRE,
}


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_checkout_session(request):
    """
    Create a Stripe Checkout session for subscription.
    
    POST /api/v1/billing/checkout/
    Body: { "tier": "pro" | "builder" | "architect" | "empire" }
    """
    tier = request.data.get('tier', '').lower()
    
    if tier not in PRICE_IDS:
        return Response({'error': f'Invalid tier: {tier}'}, status=400)
    
    price_id = PRICE_IDS[tier]
    
    try:
        # Get or create Stripe customer
        user = request.user
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                metadata={'user_id': user.id}
            )
            user.stripe_customer_id = customer.id
            user.save(update_fields=['stripe_customer_id'])
        
        # Create checkout session
        session = stripe.checkout.Session.create(
            customer=user.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f'{settings.FRONTEND_URL}/dashboard?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'{settings.FRONTEND_URL}/pricing?canceled=true',
            metadata={
                'user_id': user.id,
                'tier': tier,
            },
            automatic_tax={'enabled': True},
        )
        
        return Response({'checkout_url': session.url, 'session_id': session.id})
    
    except stripe.error.StripeError as e:
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_portal_session(request):
    """
    Create a Stripe Customer Portal session for managing subscription.
    
    POST /api/v1/billing/portal/
    """
    user = request.user
    
    if not user.stripe_customer_id:
        return Response({'error': 'No active subscription'}, status=400)
    
    try:
        session = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=f'{settings.FRONTEND_URL}/dashboard',
        )
        return Response({'portal_url': session.url})
    
    except stripe.error.StripeError as e:
        return Response({'error': str(e)}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_subscription_status(request):
    """
    Get current subscription status for the user.
    
    GET /api/v1/billing/status/
    """
    user = request.user
    
    # Check if in free trial (handled in our DB, not Stripe)
    if user.is_trial_active():
        return Response({
            'status': 'trial',
            'tier': 'trial',
            'trial_ends_at': user.trial_ends_at,
            'days_remaining': user.trial_days_remaining(),
        })
    
    if not user.stripe_customer_id or not user.stripe_subscription_id:
        return Response({
            'status': 'inactive',
            'tier': None,
        })
    
    try:
        subscription = stripe.Subscription.retrieve(user.stripe_subscription_id)
        
        return Response({
            'status': subscription.status,
            'tier': user.subscription_tier,
            'current_period_end': subscription.current_period_end,
            'cancel_at_period_end': subscription.cancel_at_period_end,
        })
    
    except stripe.error.StripeError as e:
        return Response({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(['POST'])
def stripe_webhook(request):
    """
    Handle Stripe webhook events.
    
    POST /api/v1/billing/webhook/
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse('Invalid payload', status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse('Invalid signature', status=400)
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        handle_checkout_completed(event['data']['object'])
    
    elif event['type'] == 'customer.subscription.created':
        handle_subscription_created(event['data']['object'])
    
    elif event['type'] == 'customer.subscription.updated':
        handle_subscription_updated(event['data']['object'])
    
    elif event['type'] == 'customer.subscription.deleted':
        handle_subscription_deleted(event['data']['object'])
    
    elif event['type'] == 'invoice.paid':
        handle_invoice_paid(event['data']['object'])
    
    elif event['type'] == 'invoice.payment_failed':
        handle_payment_failed(event['data']['object'])
    
    return HttpResponse(status=200)


def handle_checkout_completed(session):
    """Handle successful checkout."""
    from accounts.models import User
    
    user_id = session.get('metadata', {}).get('user_id')
    tier = session.get('metadata', {}).get('tier')
    subscription_id = session.get('subscription')
    
    if user_id:
        try:
            user = User.objects.get(id=user_id)
            user.stripe_subscription_id = subscription_id
            user.subscription_tier = tier
            user.subscription_status = 'active'
            user.save(update_fields=[
                'stripe_subscription_id', 
                'subscription_tier', 
                'subscription_status'
            ])
        except User.DoesNotExist:
            pass


def handle_subscription_created(subscription):
    """Handle new subscription."""
    from accounts.models import User
    
    customer_id = subscription.get('customer')
    
    try:
        user = User.objects.get(stripe_customer_id=customer_id)
        user.stripe_subscription_id = subscription.get('id')
        user.subscription_status = subscription.get('status')
        user.save(update_fields=['stripe_subscription_id', 'subscription_status'])
    except User.DoesNotExist:
        pass


def handle_subscription_updated(subscription):
    """Handle subscription updates (upgrades, downgrades, cancellations)."""
    from accounts.models import User
    
    customer_id = subscription.get('customer')
    
    try:
        user = User.objects.get(stripe_customer_id=customer_id)
        user.subscription_status = subscription.get('status')
        
        # Get tier from price
        items = subscription.get('items', {}).get('data', [])
        if items:
            price_id = items[0].get('price', {}).get('id')
            for tier, pid in PRICE_IDS.items():
                if pid == price_id:
                    user.subscription_tier = tier
                    break
        
        user.save(update_fields=['subscription_status', 'subscription_tier'])
    except User.DoesNotExist:
        pass


def handle_subscription_deleted(subscription):
    """Handle subscription cancellation."""
    from accounts.models import User
    
    customer_id = subscription.get('customer')
    
    try:
        user = User.objects.get(stripe_customer_id=customer_id)
        user.subscription_status = 'canceled'
        user.subscription_tier = None
        user.save(update_fields=['subscription_status', 'subscription_tier'])
    except User.DoesNotExist:
        pass


def handle_invoice_paid(invoice):
    """Handle successful payment."""
    # Log payment for records
    pass


def handle_payment_failed(invoice):
    """Handle failed payment."""
    from accounts.models import User
    
    customer_id = invoice.get('customer')
    
    try:
        user = User.objects.get(stripe_customer_id=customer_id)
        user.subscription_status = 'past_due'
        user.save(update_fields=['subscription_status'])
        # TODO: Send email notification
    except User.DoesNotExist:
        pass
