# ===================================================
# NOTICE: This file is part of a private repository.
# Provided for demonstration purposes only.
# Not suitable for production use.
# ===================================================

# resources/wal_events/models.py
import uuid
import enum
from datetime import datetime
from models import db
from sqlalchemy import Enum, JSON

class WalEventAction(enum.Enum):
    insert = "insert"
    update = "update"
    delete = "delete"

class WalEvent(db.Model):
    __tablename__ = "wal_events"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    wal_pipeline_id = db.Column(db.String(36), db.ForeignKey('postgres_replication_slots.id'), nullable=False)
    commit_lsn = db.Column(db.BigInteger, nullable=False)
    seq = db.Column(db.BigInteger, nullable=False)
    record_pks = db.Column(JSON, nullable=False)
    record = db.Column(JSON, nullable=False)
    data = db.Column(JSON, nullable=True)
    changes = db.Column(JSON)
    action = db.Column(Enum(WalEventAction), nullable=False)
    committed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    source_table_oid = db.Column(db.Integer, nullable=False)
    source_table_schema = db.Column(db.String(255), nullable=False)
    source_table_name = db.Column(db.String(255), nullable=False)
    inserted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    wal_pipeline = db.relationship("PostgresReplicationSlot", backref=db.backref("wal_events", lazy=True))

    def __repr__(self):
        return f"<WalEvent {self.id} ({self.action.value})>"
