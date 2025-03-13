# ===================================================
# NOTICE: This file is part of a private repository.
# Provided for demonstration purposes only.
# Not suitable for production use.
# ===================================================

from flask import Blueprint
from .resource import PaymentIntent, StripeWebhook, UserCredits

# Create a Blueprint for payment-related routes
payments_bp = Blueprint('payments_routes', __name__, url_prefix='/api')

# Route for creating a payment intent
@payments_bp.route('/create-payment-intent', methods=['POST'])
def create_payment_intent():
    return PaymentIntent.create_payment_intent()

# Route for Stripe webhook
@payments_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    return StripeWebhook.stripe_webhook()

# Route for getting user credits
@payments_bp.route('/user/credits', methods=['GET'])
def get_user_credits():
    return UserCredits.get_user_credits()
