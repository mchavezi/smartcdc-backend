# ===================================================
# NOTICE: This file is part of a private repository.
# Provided for demonstration purposes only.
# Not suitable for production use.
# ===================================================

import logging
from flask import Blueprint
from .resource import WalEventResource

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

wal_event_bp = Blueprint('wal_event_routes', __name__, url_prefix='/api/wal-events')

@wal_event_bp.route('/', methods=['GET'])
def list_wal_events():
    """
    Retrieve a list of WAL events with optional filtering.

    Query Parameters:
    -----------------
    - `source_table_name` (string, optional): Filter by table name.
    - `action` (string, optional): Filter by action type (`insert`, `update`, `delete`).

    Example Requests:
    -----------------
    - `GET /api/wal-events/`
    - `GET /api/wal-events/?source_table_name=users`
    - `GET /api/wal-events/?action=update`
    - `GET /api/wal-events/?source_table_name=orders&action=delete`
    """
    return WalEventResource.list_wal_events()

@wal_event_bp.route('/<string:event_id>', methods=['GET'])
def get_wal_event(event_id):
    """
    Retrieve details of a specific WAL event.

    Example Request:
    ----------------
    `GET /api/wal-events/<event_id>`
    """
    return WalEventResource.get_wal_event(event_id)

@wal_event_bp.route('/', methods=['POST'])
@jwt_required()
def create_wal_event():
    """
    Create a new WAL event.
    """
    return WalEventResource.create_wal_event()

@wal_event_bp.route('/<string:event_id>', methods=['PUT'])
@jwt_required()
def update_wal_event(event_id):
    """
    Update an existing WAL event.
    """
    return WalEventResource.update_wal_event(event_id)

@wal_event_bp.route('/<string:event_id>', methods=['DELETE'])
def delete_wal_event(event_id):
    """
    Delete a specific WAL event.

    Example Request:
    ----------------
    `DELETE /api/wal-events/<event_id>`
    """
    return WalEventResource.delete_wal_event(event_id)
