# ===================================================
# NOTICE: This file is part of a private repository.
# Provided for demonstration purposes only.
# Not suitable for production use.
# ===================================================

# resources/postgres_database/routes.py
import logging
from flask import Blueprint
from .resource import PostgresDatabaseResource
from flask_jwt_extended import jwt_required, get_jwt_identity

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

postgress_db_bp = Blueprint('postgres_database_routes', __name__, url_prefix='/api/postgres-databases')

@postgress_db_bp.route('/', methods=['GET'])
def list_postgres_databases():
    """
    List all postgres databases for the authenticated user.
    """
    return PostgresDatabaseResource.list_postgres_databases()

@postgress_db_bp.route('', methods=['POST'])
def create_postgres_database():
    """
    Create a new postgres database for the authenticated user.
    """
    return PostgresDatabaseResource.create_postgres_database()

@postgress_db_bp.route('/<string:db_id>', methods=['GET'])
def get_postgres_database(db_id):
    """
    Get details of a specific postgres database for the authenticated user.
    """
    return PostgresDatabaseResource.get_postgres_database(db_id)

@postgress_db_bp.route('/<string:db_id>', methods=['PUT'])
def update_postgres_database(db_id):
    """
    Update a specific postgres database for the authenticated user.
    """
    return PostgresDatabaseResource.update_postgres_database(db_id)

@postgress_db_bp.route('/<string:db_id>', methods=['DELETE'])
def delete_postgres_database(db_id):
    """
    Delete a specific postgres database for the authenticated user.
    """
    return PostgresDatabaseResource.delete_postgres_database(db_id)

@postgress_db_bp.route('/<string:db_id>/test-replication', methods=['POST'])
@jwt_required()
def test_db_replication_setup(db_id):
    """
    Test if the database replication setup (publication and slot) exists.
    """
    return PostgresDatabaseResource.test_db_replication_setup(db_id)
