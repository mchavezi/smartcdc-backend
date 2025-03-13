# ===================================================
# NOTICE: This file is part of a private repository.
# Provided for demonstration purposes only.
# Not suitable for production use.
# ===================================================

# resources/postgres_replication_slot/models.py
import uuid
import enum
from models import db
from sqlalchemy import Enum, JSON

class ReplicationSlotStatus(enum.Enum):
    active = "active"
    disabled = "disabled"

class PostgresReplicationSlot(db.Model):
    __tablename__ = 'postgres_replication_slots'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    publication_name = db.Column(db.String(255), nullable=False)
    slot_name = db.Column(db.String(255), nullable=False)
    status = db.Column(Enum(ReplicationSlotStatus), nullable=False, default=ReplicationSlotStatus.active)
    annotations = db.Column(JSON, default=dict)

    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    postgres_database_id = db.Column(db.String(36), db.ForeignKey('postgres_databases.id'), nullable=False)

    user = db.relationship('User', backref=db.backref('postgres_replication_slots', lazy=True))
    postgres_database = db.relationship('PostgresDatabase', backref=db.backref('postgres_replication_slots', lazy=True))

    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    @property
    def info(self):
        return {
            "publication_name": self.publication_name,
            "slot_name": self.slot_name,
            "status": self.status.value,
            "annotations": self.annotations
        }

    def __repr__(self):
        return f"<PostgresReplicationSlot {self.slot_name} ({self.status.value})>"
