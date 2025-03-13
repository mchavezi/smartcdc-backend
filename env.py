# ===================================================
# NOTICE: This file is part of a private repository.
# Provided for demonstration purposes only.
# Not suitable for production use.
# ===================================================

# from backend.models import db as base_db
# from resources.postgres_database.models import PostgresDatabase
# from resources.postgres_replication_slot.models import PostgresReplicationSlot
# from resources.wal_events.models import WalEvent

# target_metadata = base_db.metadata
from models import db as base_db
from resources.postgres_database.models import PostgresDatabase
from resources.postgres_replication_slot.models import PostgresReplicationSlot
from resources.wal_events.models import WalEvent

target_metadata = base_db.metadata
