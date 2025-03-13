# ===================================================
# NOTICE: This file is part of a private repository.
# Provided for demonstration purposes only.
# Not suitable for production use.
# ===================================================

from flask import jsonify, request, current_app
from config import Config
from models import User, db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_mail import Message
from datetime import datetime

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_RESUME_EXTENSIONS = {'pdf', 'doc', 'docx'}
UPLOAD_FOLDER = 'uploads'

class UserRegister:
    @staticmethod
    def register_user():
        data = request.get_json()
        
        # Validation
        if 'email' not in data or 'password' not in data:
            return jsonify({'message': 'Email and password are required'}), 400
        
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'message': 'User already exists'}), 400
        
        # Hashing password
        hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')
        
        # Creating new user
        new_user = User(
            name=data.get('name'), 
            email=data['email'], 
            password=hashed_password, 
            location=data.get('location'), 
            job_title=data.get('jobTitle'), 
            is_verified=False
        )
        verification_token = new_user.generate_verification_token()
        db.session.add(new_user)
        db.session.commit()
        
        # Access mail within the application context
        FRONTEND_APP_URL = Config.FRONTEND_APP_URL
        verification_url = f"{FRONTEND_APP_URL}/verify-email?token={verification_token}"
        msg = Message(
            'Verify Your Email',
            recipients=[new_user.email],
            body=f'Please click the following link to verify your email: {verification_url}

This link will expire in 1 hour.'
        )
        current_app.extensions['mail'].send(msg)
        
        return jsonify({'message': 'Registration successful. Please check your email to verify your account.'}), 201


class UserVerification:
    @staticmethod
    def verify_email(token):
        user = User.query.filter_by(verification_token=token).first()
        
        if not user:
            return jsonify({'message': 'Invalid verification token'}), 400
            
        if datetime.utcnow() > user.token_expiry:
            return jsonify({'message': 'Verification token has expired'}), 400
        
        user.is_verified = True
        user.verification_token = None
        user.token_expiry = None
        db.session.commit()
        
        return jsonify({'message': 'Email verified successfully'}), 200

class UserResendVerification:
    @staticmethod
    def resend_verification():
        data = request.get_json()
        user = User.query.filter_by(email=data['email']).first()
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
            
        if user.is_verified:
            return jsonify({'message': 'Email already verified'}), 400
        
        verification_token = user.generate_verification_token()
        db.session.commit()
        
        verification_url = f"{Config.FRONTEND_APP_URL}/verify-email?token={verification_token}"
        msg = Message(
            'Verify Your Email',
            recipients=[user.email],
            body=f'Please click the following link to verify your email: {verification_url}

This link will expire in 24 hours.'
        )
        current_app.extensions['mail'].send(msg)
        
        return jsonify({'message': 'Verification email resent'}), 200

class UserLogin:
    @staticmethod
    def login_user():
        data = request.get_json()
        # Validation
        if 'email' not in data or 'password' not in data:
            return jsonify({'message': 'Email and password are required'}), 400
        
        user = User.query.filter_by(email=data['email']).first()
        
        if not user or not check_password_hash(user.password, data['password']):
            return jsonify({'message': 'Invalid credentials'}), 401
        
        access_token = user.get_access_token()  # Assumes `get_access_token` is defined in your User model
        return jsonify({
            'access_token': access_token,
            'name': user.name,
            'email': user.email,
            'job_title': user.job_title,
            'location': user.location,
            'verified': user.is_verified
        }), 200

class UserUtils:
    @staticmethod
    def allowed_image_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

    @staticmethod
    def allowed_resume_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_RESUME_EXTENSIONS

    @staticmethod
    def init_profile_routes():
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)

class UserProfile:
    @staticmethod
    @jwt_required()
    def get_profile():
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
            
        if not user:
            return jsonify({'error': 'User not found'}), 404
                
        return jsonify({
            'name': user.name,
            'email': user.email,
            'job_title': user.job_title,
            'location': user.location,
            'profile_picture': user.profile_picture,
            'resume_filename': user.resume_filename
        })
