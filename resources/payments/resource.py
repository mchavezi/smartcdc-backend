# ===================================================
# NOTICE: This file is part of a private repository.
# Provided for demonstration purposes only.
# Not suitable for production use.
# ===================================================

import os
from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
import stripe
from models import User, db

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

class PaymentIntent:
    @staticmethod
    @jwt_required()
    def create_payment_intent():
        try:
            data = request.get_json()
            number_of_credits = data.get('credits', 1)
            
            # Calculate amount in cents (1 credit = $1 = 100 cents)
            amount = number_of_credits * 100

            # Create a PaymentIntent
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency='usd',
                metadata={'user_id': get_jwt_identity()},
            )

            return jsonify({
                'clientSecret': intent.client_secret
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 400


class StripeWebhook:
    @staticmethod
    def stripe_webhook():
        payload = request.get_data()
        sig_header = request.headers.get('Stripe-Signature')

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, os.getenv('STRIPE_WEBHOOK_SECRET')
            )
        except ValueError:
            return jsonify({'error': 'Invalid payload'}), 400
        except stripe.error.SignatureVerificationError:
            return jsonify({'error': 'Invalid signature'}), 400

        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            user_id = payment_intent['metadata']['user_id']
            credits_purchased = payment_intent['amount'] // 100  # Convert cents to dollars/credits

            # Update user's credits in database
            user = User.query.get(user_id)
            if user:
                user.resume_tokens += credits_purchased
                db.session.commit()

        return jsonify({'status': 'success'})


class UserCredits:
    @staticmethod
    @jwt_required()
    def get_user_credits():
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        return jsonify({'credits': user.resume_tokens})
