# ===================================================
# NOTICE: This file is part of a private repository.
# Provided for demonstration purposes only.
# Not suitable for production use.
# ===================================================

# resources/postgres_database/resource.py
import logging
import threading 
from flask import jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from resources.postgres_database.models import PostgresDatabase
from models import User, db
import psycopg2
from psycopg2.extras import RealDictCursor
from services.wal_listener.wal_listener_service import WALListenerService

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class PostgresDatabaseResource:
    @staticmethod
    @jwt_required()
    def list_postgres_databases():
        logger.info(" ℹ️  list_postgres_databases")
        current_user_id = get_jwt_identity()
        logger.info(" ℹ️  list_postgres_databases current_user_id %s", current_user_id)
        
        databases = PostgresDatabase.query.filter_by(user_id=current_user_id).all()
        results = []
        for db in databases:
            try:
                logger.info(" ℹ️  Database ID: %s, Name: %s, Hostname: %s", db.id, db.name, db.hostname)
                results.append({
                    "id": db.id,
                    "name": db.name,
                    "hostname": db.hostname,
                    "port": db.port,
                    "username": db.username,
                    "created_at": db.created_at,
                    "updated_at": db.updated_at,
                    "user_id": db.user_id
                })
            except AttributeError as e:
                logger.error(" ❌ AttributeError for database: %s, Error: %s", db, e)
        return jsonify(results)

    @staticmethod
    @jwt_required()
    def create_postgres_database():
        current_user_id = get_jwt_identity()
        data = request.json
        logger.info("ℹ️  create_postgres_database data: %s", data)

        new_db = PostgresDatabase(
            user_id=current_user_id,
            name=data["name"],
            db_name=data["databaseName"],
            hostname=data["hostname"],
            port=data.get("port", 5432),
            username=data["username"],
            password=data["password"],
        )
        db.session.add(new_db)
        db.session.commit()

        slot_name = data.get("slotName")
        publication_name = data.get("publicationName")
        if slot_name and publication_name:
            from models import PostgresReplicationSlot, ReplicationSlotStatus
            new_slot = PostgresReplicationSlot(
                user_id=current_user_id,
                postgres_database_id=new_db.id,
                slot_name=slot_name,
                publication_name=publication_name,
                status=ReplicationSlotStatus.active
            )
            db.session.add(new_slot)
            db.session.commit()

            # Notify WAL Listener Service about the new slot
            WALListenerService.notify_new_slot({
                "db_id": new_db.id,
                "conn_details": {
                    "dbname": new_db.db_name,
                    "host": new_db.hostname,
                    "port": new_db.port,
                    "user": new_db.username,
                    "password": new_db.password,
                },
                "slot_name": slot_name,
                "publication_name": publication_name,
            })

        return jsonify({
            "message": "PostgresDatabase created successfully",
            "id": new_db.id
        }), 201



    @staticmethod
    @jwt_required()
    def get_postgres_database(db_id):
        current_user_id = get_jwt_identity()
        database = PostgresDatabase.query.filter_by(id=db_id, user_id=current_user_id).first_or_404()
        return jsonify({
            "id": database.id,
            "name": database.name,
            "db_name": database.db_name,
            "hostname": database.hostname,
            "port": database.port,
            "username": database.username,
            "created_at": database.created_at,
            "updated_at": database.updated_at
        })

    @staticmethod
    @jwt_required()
    def update_postgres_database(db_id):
        current_user_id = get_jwt_identity()
        database = PostgresDatabase.query.filter_by(id=db_id, user_id=current_user_id).first_or_404()
        data = request.json
        database.name = data.get("name", database.name)
        database.hostname = data.get("hostname", database.hostname)
        database.port = data.get("port", database.port)
        database.username = data.get("username", database.username)
        database.password = data.get("password", database.password)
        db.session.commit()
        return jsonify({"message": "PostgresDatabase updated successfully"})

    @staticmethod
    @jwt_required()
    def delete_postgres_database(db_id):
        """
        Deletes a Postgres database and its associated replication slots.
        Ensures any active replication slot is terminated before being dropped.
        """
        current_user_id = get_jwt_identity()
        database = PostgresDatabase.query.filter_by(id=db_id, user_id=current_user_id).first_or_404()

        # Drop replication slots in Postgres before deleting the database
        for slot in database.postgres_replication_slots:
            slot_name = slot.slot_name
            try:
                logger.info("ℹ️ Dropping replication slot '%s' for database ID %s", slot_name, db_id)
                connection_details = {
                    "dbname": database.db_name,
                    "host": database.hostname,
                    "port": database.port,
                    "user": database.username,
                    "password": database.password,
                }
                with psycopg2.connect(**connection_details) as conn:
                    with conn.cursor() as cursor:
                        # Check for active PID using the slot
                        # cursor.execute("SELECT active_pid FROM pg_replication_slots WHERE slot_name = %s;", (slot_name,))
                        # result = cursor.fetchone()
                        # if result and result[0]:  # If active_pid is not NULL
                        #     logger.warning("❗ Slot '%s' is active for PID %s. Terminating...", slot_name, result[0])
                        #     cursor.execute("SELECT pg_terminate_backend(%s);", (result[0],))
                        #     logger.info("✅ Terminated PID %s using slot '%s'.", result[0], slot_name)

                        # Drop the replication slot
                        # cursor.execute("SELECT pg_drop_replication_slot(%s);", (slot_name,))
                        # logger.info("✅ Successfully dropped replication slot '%s'", slot_name)
                        cursor.execute("SELECT active_pid FROM pg_replication_slots WHERE slot_name = %s", (slot_name,))
                        result = cursor.fetchone()
                        if result and result[0]:
                            logger.warning(f"Slot {slot_name} is already in use by PID {result[0]}. Checking process status...")
                            # Optional: Check if the process is still alive before terminating
                            cursor.execute("SELECT pg_backend_pid();")
                            current_pid = cursor.fetchone()[0]
                            if result[0] != current_pid:
                                logger.info(f"Terminating old process {result[0]} for slot {slot_name}.")
                                cursor.execute("SELECT pg_terminate_backend(%s);", (result[0],))
                            else:
                                logger.info(f"Skipping termination, process {result[0]} is still in use.")
            except psycopg2.Error as e:
                logger.error("❌ Failed to drop replication slot '%s': %s", slot_name, e)
            except Exception as e:
                logger.error("❌ Unexpected error when dropping replication slot '%s': %s", slot_name, e)

        # Delete associated replication slot records
        for slot in database.postgres_replication_slots:
            db.session.delete(slot)

        # Delete the database record
        db.session.delete(database)
        db.session.commit()

        return jsonify({"message": "PostgresDatabase and associated replication slots deleted successfully"})

    @staticmethod
    @jwt_required()
    def test_db_replication_setup(db_id):
        logger.info(" ℹ️  test_db_replication_setup db_id: %s", db_id)
        current_user_id = get_jwt_identity()
        logger.info(" ℹ️  test_db_replication_setup current_user_id: %s", current_user_id)
 
        request_data = request.json
        logger.info(" ℹ️  test_db_replication_setup request_data: %s", request_data)
        
        slot_name = request_data.get("slotName", "slotName NOT SET!")
        publication_name = request_data.get("publicationName", "publicationName NOT SET!")
        dbname = request_data.get("databaseName", "name NOT SET!")
        hostname = request_data.get("hostname", "hostname NOT SET!")
        port = request_data.get("port", "port NOT SET!")
        username = request_data.get("username", "username NOT SET!")
        password = request_data.get("password", "password NOT SET!")

        logger.info(" 😬  test_db_replication_setup slot_name: %s", slot_name)
        logger.info(" 😬  test_db_replication_setup publication_name: %s", publication_name)
        logger.info(" 😬  test_db_replication_setup dbname: %s", dbname)
        logger.info(" 😬  test_db_replication_setup hostname: %s", hostname)
        logger.info(" 😬  test_db_replication_setup port: %s", port)
        logger.info(" 😬  test_db_replication_setup username: %s", username)

        connection_details = {
            "dbname": dbname,
            "host": hostname,
            "port": port,
            "user": username,
            "password": password,
        }

        try:
            conn = psycopg2.connect(**connection_details)
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("SELECT * FROM pg_publication WHERE pubname = %s;", (publication_name,))
            publication_result = cursor.fetchone()
            logger.info(" 😬  test_db_replication_setup publication_result: %s", publication_result)
            cursor.execute("SELECT * FROM pg_replication_slots WHERE slot_name = %s;", (slot_name,))
            replication_slot_result = cursor.fetchone()

            return jsonify({
                "publication_exists": bool(publication_result),
                "replication_slot_exists": bool(replication_slot_result),
            }), 200
        except Exception as e:
            logger.error(" ❌ Error during test_db_replication_setup: %s", e)
            return jsonify({"error": str(e)}), 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
