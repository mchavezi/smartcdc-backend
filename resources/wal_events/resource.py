# ===================================================
# NOTICE: This file is part of a private repository.
# Provided for demonstration purposes only.
# Not suitable for production use.
# ===================================================

import logging
from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from resources.wal_events.models 
    import WalEvent, WalEventAction

logger = logging.getLogger(__name__)

class WalEventResource:
    """
    Resource class for handling WAL event-related operations.
    Provides CRUD functionality, including filtering based on `source_table_name` and `action`.
    """

    @staticmethod
    @jwt_required()
    def list_wal_events():
        """
        List all WAL events for the authenticated user with optional filtering.

        Query Parameters:
        -----------------
        - `source_table_name` (string, optional): Filter WAL events by table name.
        - `action` (string, optional): Filter by action type (`insert`, `update`, or `delete`).

        Example Requests:
        -----------------
        - Get all WAL events:
          `GET /api/wal-events/`

        - Get WAL events for a specific table:
          `GET /api/wal-events/?source_table_name=users`

        - Get WAL events of a specific action:
          `GET /api/wal-events/?action=update`

        - Get WAL events for a table with a specific action:
          `GET /api/wal-events/?source_table_name=orders&action=delete`

        Returns:
        --------
        - `200 OK`: List of WAL events matching the filters.
        - `400 Bad Request`: If an invalid `action` type is provided.
        """
        current_user_id = get_jwt_identity()
        source_table_name = request.args.get("source_table_name")
        action = request.args.get("action")

        logger.info("ℹ️ Listing WAL events for user %s", current_user_id)

        query = (
            WalEvent.query
            .join(WalEvent.wal_pipeline)
            .filter(WalEvent.wal_pipeline.has(user_id=current_user_id))
        )

        if source_table_name:
            query = query.filter(WalEvent.source_table_name == source_table_name)

        if action:
            try:
                # Validate action against the Enum values
                action_enum = WalEventAction[action]
                query = query.filter(WalEvent.action == action_enum)
            except KeyError:
                return jsonify({"error": "Invalid action type"}), 400

        events = query.all()

        results = []
        for event in events:
            results.append({
                "id": event.id,
                "wal_pipeline_id": event.wal_pipeline_id,
                "commit_lsn": event.commit_lsn,
                "seq": event.seq,
                "record_pks": event.record_pks,
                "record": event.record,
                "changes": event.changes,
                "action": event.action.value,  # Enum -> String
                "committed_at": event.committed_at,
                "replication_message_trace_id": event.replication_message_trace_id,
                "source_table_oid": event.source_table_oid,
                "source_table_schema": event.source_table_schema,
                "source_table_name": event.source_table_name,
                "inserted_at": event.inserted_at
            })
        return jsonify(results), 200

    @staticmethod
    @jwt_required()
    def get_wal_event(event_id):
        """
        Retrieve details of a specific WAL event.

        Example Request:
        ----------------
        `GET /api/wal-events/<event_id>`

        Returns:
        --------
        - `200 OK`: WAL event details.
        - `404 Not Found`: If the event does not exist or does not belong to the authenticated user.
        """
        current_user_id = get_jwt_identity()
        event = (
            WalEvent.query
            .join(WalEvent.wal_pipeline)
            .filter(WalEvent.id == event_id, WalEvent.wal_pipeline.has(user_id=current_user_id))
            .first_or_404()
        )

        return jsonify({
            "id": event.id,
            "wal_pipeline_id": event.wal_pipeline_id,
            "commit_lsn": event.commit_lsn,
            "seq": event.seq,
            "record_pks": event.record_pks,
            "record": event.record,
            "changes": event.changes,
            "action": event.action.value,
            "committed_at": event.committed_at,
            "replication_message_trace_id": event.replication_message_trace_id,
            "source_table_oid": event.source_table_oid,
            "source_table_schema": event.source_table_schema,
            "source_table_name": event.source_table_name,
            "inserted_at": event.inserted_at
        })

    @staticmethod
    @jwt_required()
    def create_wal_event():
        """
        Create a new WAL event record.
        This endpoint is useful for testing or administrative purposes.
        """
        current_user_id = get_jwt_identity()
        data = request.json
        logger.info("ℹ️ Creating WAL event with data: %s", data)

        # Validate that the provided replication slot belongs to the user.
        slot_id = data.get("wal_pipeline_id")
        if not slot_id:
            return jsonify({"error": "wal_pipeline_id is required"}), 400

        slot = PostgresReplicationSlot.query.filter_by(id=slot_id, user_id=current_user_id).first_or_404()

        # Validate action type
        try:
            action = WalEventAction[data["action"]]
        except KeyError:
            return jsonify({"error": "Invalid action type"}), 400

        new_event = WalEvent(
            wal_pipeline_id = slot.id,
            commit_lsn = data["commit_lsn"],
            seq = data["seq"],
            record_pks = data["record_pks"],
            record = data["record"],
            changes = data.get("changes"),
            action = action,
            committed_at = data.get("committed_at", datetime.utcnow()),
            source_table_oid = data["source_table_oid"],
            source_table_schema = data["source_table_schema"],
            source_table_name = data["source_table_name"],
            inserted_at = data.get("inserted_at", datetime.utcnow())
        )
        db.session.add(new_event)
        db.session.commit()
        return jsonify({"message": "WAL event created", "id": new_event.id}), 201

    @staticmethod
    @jwt_required()
    def update_wal_event(event_id):
        """
        Update an existing WAL event record.
        (While WAL events are typically immutable, this endpoint is provided for testing/administrative purposes.)
        """
        current_user_id = get_jwt_identity()
        event = (
            WalEvent.query
            .join(WalEvent.wal_pipeline)
            .filter(WalEvent.id == event_id, WalEvent.wal_pipeline.has(user_id=current_user_id))
            .first_or_404()
        )
        data = request.json
        logger.info("ℹ️ Updating WAL event %s with data: %s", event_id, data)

        # Allow updating selected fields.
        if "record_pks" in data:
            event.record_pks = data["record_pks"]
        if "record" in data:
            event.record = data["record"]
        if "changes" in data:
            event.changes = data["changes"]
        if "action" in data:
            try:
                event.action = WalEventAction[data["action"]]
            except KeyError:
                return jsonify({"error": "Invalid action type"}), 400
        if "commit_lsn" in data:
            event.commit_lsn = data["commit_lsn"]
        if "seq" in data:
            event.seq = data["seq"]
        if "committed_at" in data:
            event.committed_at = data["committed_at"]
        if "source_table_oid" in data:
            event.source_table_oid = data["source_table_oid"]
        if "source_table_schema" in data:
            event.source_table_schema = data["source_table_schema"]
        if "source_table_name" in data:
            event.source_table_name = data["source_table_name"]
        if "inserted_at" in data:
            event.inserted_at = data["inserted_at"]

        db.session.commit()
        return jsonify({"message": "WAL event updated"}), 200

    @staticmethod
    @jwt_required()
    def delete_wal_event(event_id):
        """
        Delete a WAL event record.

        Example Request:
        ----------------
        `DELETE /api/wal-events/<event_id>`

        Returns:
        --------
        - `200 OK`: Confirmation that the WAL event was deleted.
        - `404 Not Found`: If the event does not exist or does not belong to the authenticated user.
        """
        current_user_id = get_jwt_identity()
        event = (
            WalEvent.query
            .join(WalEvent.wal_pipeline)
            .filter(WalEvent.id == event_id, WalEvent.wal_pipeline.has(user_id=current_user_id))
            .first_or_404()
        )

        db.session.delete(event)
        db.session.commit()
        return jsonify({"message": "WAL event deleted"}), 200
