# ===================================================
# NOTICE: This file is part of a private repository.
# Provided for demonstration purposes only.
# Not suitable for production use.
# ===================================================

# resources/postgres_database/models.py
import uuid
from datetime import datetime
from models import db 

class PostgresDatabase(db.Model):
    __tablename__ = 'postgres_databases'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    db_name = db.Column(db.String(255), nullable=False)
    hostname = db.Column(db.String(255), nullable=False)
    port = db.Column(db.Integer, nullable=False, default=5432)
    username = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    user = db.relationship('User', backref=db.backref('postgres_databases', lazy=True))
