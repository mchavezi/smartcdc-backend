# ===================================================
# NOTICE: This file is part of a private repository.
# Provided for demonstration purposes only.
# Not suitable for production use.
# ===================================================

from flask import Blueprint
from .resource import UserRegister, UserVerification, UserResendVerification, UserLogin

user_bp = Blueprint('user_routes', __name__, url_prefix='/api/user')

@user_bp.route('/register', methods=['POST'])
def register():
    return UserRegister.register_user()

@user_bp.route('/verify-email/<token>', methods=['GET'])
def verify_email(token):
    return UserVerification.verify_email(token)

@user_bp.route('/resend-verification', methods=['POST'])
def resend_verification():
    return UserResendVerification.resend_verification()

@user_bp.route('/login', methods=['POST'])
def login():
    return UserLogin.login_user()

@user_bp.route('/profile', methods=['GET'])
def get_profile():
    return UserProfile.get_profile()
