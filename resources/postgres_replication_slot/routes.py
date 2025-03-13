# ===================================================
# NOTICE: This file is part of a private repository.
# Provided for demonstration purposes only.
# Not suitable for production use.
# ===================================================

import logging
from flask import Blueprint
from .resource import PostgresReplicationSlotResource

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

replication_slot_bp = Blueprint('replication_slot_routes', __name__, url_prefix='/api/replication-slots')

@replication_slot_bp.route('/', methods=['GET'])
def list_replication_slots():
    return PostgresReplicationSlotResource.list_replication_slots()

@replication_slot_bp.route('', methods=['POST'])
def create_replication_slot():
    return PostgresReplicationSlotResource.create_replication_slot()

@replication_slot_bp.route('/<string:slot_id>', methods=['GET'])
def get_replication_slot(slot_id):
    return PostgresReplicationSlotResource.get_replication_slot(slot_id)

@replication_slot_bp.route('/<string:slot_id>', methods=['PUT'])
def update_replication_slot(slot_id):
    return PostgresReplicationSlotResource.update_replication_slot(slot_id)

@replication_slot_bp.route('/<string:slot_id>', methods=['DELETE'])
def delete_replication_slot(slot_id):
    return PostgresReplicationSlotResource.delete_replication_slot(slot_id)
