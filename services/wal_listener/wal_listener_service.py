# ===================================================
# NOTICE: This file is part of a private repository.
# Provided for demonstration purposes only.
# Not suitable for production use.
# ===================================================

# services/wal_listener/wal_listener_service.py
"""
A microservice that:
1) Connects to your "application DB" in MySQL using PyMySQL, reading ENV variables DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
2) Fetches "active" replication slots, each referencing a user's Postgres DB
3) Spawns a thread to stream WAL from each user DB using psycopg2 (LogicalReplicationConnection).
"""
import os
import time
import logging
import threading
from typing import Dict

import pymysql
from pymysql.cursors import DictCursor
from psycopg2.extras import RealDictCursor

import psycopg2
from psycopg2.extras import LogicalReplicationConnection

from dotenv import load_dotenv

from sqlalchemy import Enum, JSON

try:
    # from services.wal_listener.postgres_decoder import decode_message
    from .postgres_decoder import decode_message
except ImportError:
    from postgres_decoder import decode_message

load_dotenv()

APPDB_USER = os.getenv('DB_USER', 'DB_USER NOT SET!')
APPDB_PASSWORD = os.getenv('DB_PASSWORD', 'DB_PASSWORD NOT SET!')
APPDB_HOST = os.getenv('DB_HOST', 'DB_HOST NOT SET!')
APPDB_NAME = os.getenv('DB_NAME', 'DB_NAME NOT SET!')
APPDB_PORT = int(os.getenv("DB_PORT", 'DB_PORT NOT SET!'))

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class WALListenerService:
    """
    Runs forever. Every 'check_interval' seconds:
      - Connect to MySQL (the "application DB") to find which user DBs are active
      - For each user DB, if no thread is running, start one
      - If a user DB is no longer active, stop that thread
    """
    subscriptions = {}

    def __init__(self, check_interval=3):
        self.check_interval = check_interval
        self.run_flag = True
        # track { db_id -> (thread, run_status_dict) }
        self.subscriptions = {}

    def start(self):
        """
        Start the WAL Listener service. This runs an infinite loop
        to check for active replication slots at regular intervals.
        """
        logger.info("WAL Listener Service started.")
        while self.run_flag:
            try:
                self.refresh_subscriptions()
            except Exception as e:
                logger.exception("Error refreshing subscriptions: %s", e)
            time.sleep(self.check_interval)

    def stop(self):
        """
        Stop the WAL Listener service gracefully by stopping all threads.
        """
        logger.info("Stopping WAL Listener Service...")
        self.run_flag = False
        for db_id, (thread, run_status) in list(self.subscriptions.items()):
            run_status["running"] = False

    def refresh_subscriptions(self):
        """
        Fetch from MySQL which Postgres DBs have an active replication slot.
        Then, start or stop threads accordingly.
        """
        active_slots = self.fetch_active_slots()
        desired_db_ids = set()
        db_info_map = {}

        for row in active_slots:
            db_id = row["db_id"]
            desired_db_ids.add(db_id)
            if db_id not in db_info_map:
                db_info_map[db_id] = {
                    "conn_details": row["conn_details"],
                    "slot_name": row["slot_name"],
                    "publication_name": row["publication_name"],
                }

        # Stop threads for DBs no longer active
        for db_id in list(self.subscriptions.keys()):
            if db_id not in desired_db_ids:
                _, run_status = self.subscriptions[db_id]
                run_status["running"] = False
                del self.subscriptions[db_id]
                logger.info("db_id=%s: Marked WAL thread for stop", db_id)

        # Start threads for newly active DBs
        for db_id, info in db_info_map.items():
            if db_id not in self.subscriptions:
                logger.info("Starting new WAL thread for db_id=%s", db_id)
                run_status = {"running": True}
                t = threading.Thread(
                    target=self._wal_loop,
                    args=(
                        db_id,
                        info["conn_details"],
                        info["slot_name"],
                        info["publication_name"],
                        run_status
                    ),
                    daemon=True
                )
                self.subscriptions[db_id] = (t, run_status)
                t.start()

    def fetch_active_slots(self):
        """
        Query MySQL to find rows in 'postgres_replication_slots' with status='active',
        joined with 'postgres_databases' for user credentials.

        Returns:
            list: A list of dictionaries representing the active slots, each with:
                  - db_id: The database ID.
                  - conn_details: Connection details for the Postgres DB.
                  - slot_name: The replication slot name.
                  - publication_name: The publication name.
        """
        rows = []
        query = """
        SELECT
          pd.id AS db_id,
          pd.db_name AS dbname,
          pd.hostname,
          pd.port,
          pd.username,
          pd.password,
          prs.slot_name,
          prs.publication_name
        FROM postgres_databases pd
        JOIN postgres_replication_slots prs ON pd.id = prs.postgres_database_id
        WHERE prs.status = 'active'
        """

        try:
            conn = pymysql.connect(
                host=APPDB_HOST,
                port=APPDB_PORT,
                user=APPDB_USER,
                password=APPDB_PASSWORD,
                database=APPDB_NAME,
                cursorclass=DictCursor
            )
            with conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    for row in cur.fetchall():
                        conn_details = {
                            "dbname": row["dbname"],
                            "host": row["hostname"],
                            "port": row["port"],
                            "user": row["username"],
                            "password": row["password"],
                        }
                        rows.append({
                            "db_id": row["db_id"],
                            "conn_details": conn_details,
                            "slot_name": row["slot_name"],
                            "publication_name": row["publication_name"]
                        })
        except Exception as e:
            logger.exception("Failed to fetch active replication slots from MySQL: %s", e)

        return rows

    @staticmethod
    def _wal_loop(db_id, conn_details, slot_name, publication_name, run_status):
        logger.info("ℹ️ WAL loop starting for db_id=%s", db_id)
        connection = None
        current_tx = {}
        try:
            connection = psycopg2.connect(
                connection_factory=LogicalReplicationConnection,
                **conn_details
            )
            cur = connection.cursor()

            # Fetch the current backend process ID
            cur.execute("SELECT pg_backend_pid();")
            backend_pid = cur.fetchone()[0]

            logger.info("ℹ️ db_id=%s: Backend PID=%s", db_id, backend_pid)

            cur.execute("SELECT active_pid FROM pg_replication_slots WHERE slot_name = %s", (slot_name,))
            result = cur.fetchone()
            if result and result[0]:
                logger.warning(f"Slot {slot_name} is already in use by PID {result[0]}. Reclaiming...")
                cur.execute("SELECT pg_terminate_backend(%s);", (result[0],))
                logger.info(f"💣 Terminated PID {result[0]} using slot {slot_name}.")

            logger.info("🏁 db_id=%s: START_REPLICATION slot=%s publication=%s pid=%s",
                        db_id, slot_name, publication_name, backend_pid)

            cur.start_replication(
                slot_name=slot_name,
                options={
                    "proto_version": "1",
                    "publication_names": publication_name
                }
            )

            relation_cache = {}

            def decode_record_data(record_hex, relation_msg):
                """
                Decode the raw tuple hex string into a dictionary mapping column names
                to their decoded (text) values. This assumes that the raw tuple was encoded
                as a series of columns where each column is prefixed by:
                  - 1 byte marker: 't' for text, 'n' for null, or 'u' for unchanged
                  - If marker is 't': 4 bytes (big-endian) indicating the length,
                    followed by that many bytes representing the text value.
                """
                record_bytes = bytes.fromhex(record_hex)
                columns = relation_msg.get("columns", [])
                decoded = {}
                offset = 0
                for col in columns:
                    if offset >= len(record_bytes):
                        break  # no more data
                    # Read the 1-byte marker
                    marker = chr(record_bytes[offset])
                    offset += 1
                    if marker == 't':
                        if offset + 4 > len(record_bytes):
                            decoded[col] = None
                            break
                        length = int.from_bytes(record_bytes[offset:offset+4], byteorder='big')
                        offset += 4
                        value_bytes = record_bytes[offset:offset+length]
                        offset += length
                        try:
                            decoded[col] = value_bytes.decode('utf-8')
                        except Exception:
                            decoded[col] = value_bytes.hex()
                    elif marker == 'n':  # column is NULL
                        decoded[col] = None
                    elif marker == 'u':  # unchanged
                        decoded[col] = "unchanged"
                    else:
                        decoded[col] = None
                return decoded


            def build_wal_event(tx):
                # Use cached relation if not present in current transaction
                relation_msg = tx.get("relation")
                if relation_msg is None:
                    # Try to fetch the relation message from the cache using the relation_id from the change message.
                    change_msg = tx.get("change")
                    if change_msg:
                        relation_id = change_msg.get("relation_id")
                        relation_msg = relation_cache.get(relation_id)
                        if relation_msg is None:
                            logger.error("Missing relation metadata for relation_id %s and no cached value.", relation_id)
                            return None
                    else:
                        logger.error("No change message to determine relation_id.")
                        return None

                # Cache the relation info for future transactions.
                if "relation_id" in relation_msg:
                    relation_cache[relation_msg["relation_id"]] = relation_msg

                # Ensure all parts are available.
                required = ["begin", "change", "commit"]
                for part in required:
                    if part not in tx or tx[part] is None:
                        logger.error("Missing required transaction part: %s. Current tx: %s", part, tx)
                        return None

                commit_msg = tx["commit"]
                change_msg = tx["change"]
                begin_msg = tx["begin"]

                commit_lsn_int = lsn_to_int(commit_msg["lsn"])
                seq = commit_lsn_int + begin_msg["xid"]  # simplistic example

        
                record = build_record(change_msg, relation_msg)

                data = None
                if isinstance(record, str):
                    try:
                        data = decode_record_data(record, relation_msg)
                    except Exception as e:
                        logger.error("Error decoding record data: %s", e)
                elif isinstance(record, dict):
                    # If build_record already returned a dict, just use it.
                    data = record

                changes = None
                if change_msg["type"] == "update" and "old_fields" in change_msg:
                    changes = build_changes(change_msg["old_fields"], change_msg.get("fields", {}))

                # Retrieve schema and table names.
                source_table_schema = (
                    relation_msg.get("nspname")
                    or relation_msg.get("schema")
                    or "public"
                )
                source_table_name = (
                    relation_msg.get("relation_name")
                    or relation_msg.get("table")
                    or "unknown"
                )

                wal_event = {
                    "commit_lsn": commit_lsn_int,
                    "seq": seq,
                    "record_pks": [str(x) for x in change_msg.get("ids", [])],
                    "record": record,
                    "data": data,
                    "changes": changes,
                    "action": change_msg["type"],
                    "committed_at": commit_msg["commit_timestamp"].isoformat(),
                    "source_table_oid": relation_msg.get("table_oid", relation_msg.get("relation_id")),
                    "source_table_schema": source_table_schema,
                    "source_table_name": source_table_name
                }
                return wal_event


            def lsn_to_int(lsn_tuple):
                """
                Convert an LSN represented as a tuple (xlog_file, xlog_offset) into an integer.
                (Your implementation may vary.)
                """
                xlog_file, xlog_offset = lsn_tuple
                # For example, assume 32 bits for offset:
                return (xlog_file << 32) | xlog_offset

            def build_record(change_msg, relation_msg):
                """
                Build a record from the change message and relation metadata.
                
                If the change message contains a raw tuple value (tuple_raw),
                then return that raw hex string. Otherwise, if a decoded tuple
                is provided, zip it with the column names from the relation message.
                """
                logger.debug("🐞 [build_record] Received change_msg: %s", change_msg)
                logger.debug("🐞 [build_record] Received relation_msg: %s", relation_msg)
                
                # If a raw tuple exists, use it as the record.
                tuple_raw = change_msg.get("tuple_raw")
                if tuple_raw:
                    logger.info("ℹ️ [build_record] Using raw tuple value as record: %s", tuple_raw)
                    return tuple_raw  # Return the raw hex string without decoding.
                
                # Otherwise, try to use a decoded tuple (if present)
                values = change_msg.get("tuple", [])
                columns = relation_msg.get("columns", [])
                
                if not values:
                    logger.error("🚨 [build_record] No tuple or tuple_raw found in change_msg: %s", change_msg)
                    return None

                record = dict(zip(columns, values))
                if not record:
                    logger.error("🚨 [build_record] Record is empty after zipping columns: %s with values: %s", columns, values)
                else:
                    logger.debug("🐞 [build_record] Constructed record: %s", record)
                return record


            def build_changes(old_fields, new_fields):
                """
                Compare old and new field values and return a dict of changes.
                """
                changes = {}
                for key, old_value in old_fields.items():
                    new_value = new_fields.get(key)
                    if new_value != old_value:
                        changes[key] = old_value  # or perhaps {old: old_value, new: new_value}
                return changes


            def process_wal_event(wal_event):
                """
                Persist the constructed wal_event into the wal_events table.
                """
                logger.debug("🤖 Constructed wal_event: %s", wal_event)
                try:
                    # Import your Flask app (update the import according to your project structure)
                    from app import create_app
                    app = create_app()

                    # Push the application context for this block
                    with app.app_context():
                        from models import db
                        from resources.wal_events.models import WalEvent, WalEventAction
                        from resources.postgres_replication_slot.models import PostgresReplicationSlot
                        import datetime

                        # Look up the replication slot record to obtain the wal_pipeline_id.
                        rep_slot = PostgresReplicationSlot.query.filter_by(
                            postgres_database_id=db_id,
                            slot_name=slot_name
                        ).first()
                        if not rep_slot:
                            logger.error("Could not find replication slot for db_id=%s and slot_name=%s", db_id, slot_name)
                            return

                        # Convert committed_at to a datetime if needed.
                        committed_at = wal_event.get("committed_at")
                        if isinstance(committed_at, str):
                            committed_at = datetime.datetime.fromisoformat(committed_at)

                        # Create a new WalEvent record.
                        new_event = WalEvent(
                            wal_pipeline_id=rep_slot.id,
                            commit_lsn=wal_event["commit_lsn"],
                            seq=wal_event["seq"],
                            record_pks=wal_event["record_pks"],
                            record=wal_event["record"],
                            data=wal_event["data"],
                            changes=wal_event["changes"],
                            action=WalEventAction[wal_event["action"]],
                            committed_at=committed_at,
                            source_table_oid=wal_event["source_table_oid"],
                            source_table_schema=wal_event["source_table_schema"],
                            source_table_name=wal_event["source_table_name"]
                        )
                        db.session.add(new_event)
                        db.session.commit()
                        logger.info("ℹ️ Saved WAL event with id: %s", new_event.id)
                except Exception as e:
                    logger.exception("❌ Error saving WAL event: %s", e)


            def wal_callback(msg):
                nonlocal current_tx
                if not run_status["running"]:
                    raise RuntimeError("🪑 WAL loop stopping: run_status set to False.")
                try:
                    decoded_message = decode_message(msg.payload)
                    logger.debug("🐞 db_id=%s Decoded WAL msg: %s", db_id, decoded_message)
                    
                    msg_type = decoded_message.get("type")
                    if msg_type == "begin":
                        current_tx["begin"] = decoded_message
                    elif msg_type == "relation":
                        current_tx["relation"] = decoded_message
                    elif msg_type in ["insert", "update", "delete"]:
                        current_tx["change"] = decoded_message
                    elif msg_type == "commit":
                        current_tx["commit"] = decoded_message
                        wal_event = build_wal_event(current_tx)
                        if wal_event is not None:
                            logger.info("ℹ️  Constructed wal_event: %s", wal_event)
                            process_wal_event(wal_event)
                        else:
                            logger.error("🚨 Could not construct wal_event due to missing parts: %s", current_tx)
                        current_tx = {}
                except Exception as e:
                    logger.error("🚨 db_id=%s Error decoding WAL message: %s", db_id, e)
                finally:
                    msg.cursor.send_feedback(flush_lsn=msg.data_start)

            cur.consume_stream(wal_callback)

        except RuntimeError as e:
            logger.info("ℹ️ db_id=%s: Stopping WAL loop due to: %s", db_id, e)
        except psycopg2.Error as e:
            logger.error("🚨 db_id=%s error in WAL loop: %s. Reconnect in 20s...", db_id, e)
            time.sleep(20)
        finally:
            if connection:
                logger.info("ℹ️ db_id=%s: Closing replication connection.", db_id)
                connection.close()

    @classmethod
    def notify_new_slot(cls, slot_details: dict):
        db_id = slot_details["db_id"]
        if db_id in cls.subscriptions:
            logger.info("ℹ️ db_id=%s: WAL Listener already running", db_id)
            return

        logger.info("ℹ️ Starting WAL Listener for new db_id=%s", db_id)
        run_status = {"running": True}
        t = threading.Thread(
            target=cls._wal_loop,
            args=(
                db_id,
                slot_details["conn_details"],
                slot_details["slot_name"],
                slot_details["publication_name"],
                run_status
            ),
            daemon=True
        )
        cls.subscriptions[db_id] = (t, run_status)
        t.start()

if __name__ == "__main__":
    service = WALListenerService(check_interval=3)
    try:
        service.start()
    except KeyboardInterrupt:
        service.stop()
        logger.info("ℹ️ WAL Listener Service stopped via keyboard interrupt.")
