# ===================================================
# NOTICE: This file is part of a private repository.
# Provided for demonstration purposes only.
# Not suitable for production use.
# ===================================================

# resources/postgres_replication_slot/resource.py
import logging
from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from resources.postgres_replication_slot.models 
    import PostgresReplicationSlot, ReplicationSlotStatus

logger = logging.getLogger(__name__)

class PostgresReplicationSlotResource:
    @staticmethod
    @jwt_required()
    def list_replication_slots():
        """
        List all replication slots for the authenticated user.
        """
        current_user_id = get_jwt_identity()
        logger.info("ℹ️  Listing replication slots for user %s", current_user_id)

        slots = PostgresReplicationSlot.query.filter_by(user_id=current_user_id).all()
        results = []
        for slot in slots:
            results.append({
                "id": slot.id,
                "publication_name": slot.publication_name,
                "slot_name": slot.slot_name,
                "status": slot.status.value,  # enum => string
                "postgres_database_id": slot.postgres_database_id,
                "created_at": slot.created_at,
                "updated_at": slot.updated_at
            })
        return jsonify(results), 200

    @staticmethod
    @jwt_required()
    def create_replication_slot():
        """
        Create a new replication slot record for the authenticated user.
        (Typically you'd do this automatically when creating the PostgresDatabase,
         but you can also expose this directly if desired.)
        """
        current_user_id = get_jwt_identity()
        data = request.json
        logger.info("ℹ️  create_replication_slot data: %s", data)

        # Typically, you'd validate that the postgres_database_id belongs to the same user.
        new_slot = PostgresReplicationSlot(
            user_id=current_user_id,
            postgres_database_id=data["postgres_database_id"],
            publication_name=data["publication_name"],
            slot_name=data["slot_name"],
            status=ReplicationSlotStatus.active  # default active
        )
        db.session.add(new_slot)
        db.session.commit()

        return jsonify({
            "message": "ReplicationSlot created",
            "id": new_slot.id,
            "status": new_slot.status.value
        }), 201

    @staticmethod
    @jwt_required()
    def get_replication_slot(slot_id):
        """
        Retrieve details of a specific replication slot.
        """
        current_user_id = get_jwt_identity()
        slot = PostgresReplicationSlot.query.filter_by(id=slot_id, user_id=current_user_id).first_or_404()
        return jsonify({
            "id": slot.id,
            "publication_name": slot.publication_name,
            "slot_name": slot.slot_name,
            "status": slot.status.value,
            "annotations": slot.annotations,
            "postgres_database_id": slot.postgres_database_id,
            "created_at": slot.created_at,
            "updated_at": slot.updated_at
        })

    @staticmethod
    @jwt_required()
    def update_replication_slot(slot_id):
        """
        Update an existing replication slot (e.g. change status from active->disabled).
        """
        current_user_id = get_jwt_identity()
        slot = PostgresReplicationSlot.query.filter_by(id=slot_id, user_id=current_user_id).first_or_404()

        data = request.json
        if "publication_name" in data:
            slot.publication_name = data["publication_name"]
        if "slot_name" in data:
            slot.slot_name = data["slot_name"]
        if "status" in data:
            # Validate it's either 'active' or 'disabled':
            if data["status"] in ReplicationSlotStatus._value2member_map_:
                slot.status = ReplicationSlotStatus(data["status"])
            else:
                return jsonify({"error": "Invalid status"}), 400

        db.session.commit()
        return jsonify({"message": "ReplicationSlot updated", "status": slot.status.value})

    @staticmethod
    @jwt_required()
    def delete_replication_slot(slot_id):
        """
        Delete a replication slot record. (Does not drop the actual slot from Postgres.)
        """
        current_user_id = get_jwt_identity()
        slot = PostgresReplicationSlot.query.filter_by(id=slot_id, user_id=current_user_id).first_or_404()

        db.session.delete(slot)
        db.session.commit()
        return jsonify({"message": "ReplicationSlot deleted"}), 200
