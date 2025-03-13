# ===================================================
# NOTICE: This file is part of a private repository.
# Provided for demonstration purposes only.
# Not suitable for production use.
# ===================================================

# services/postgres_decoder.py
"""
Provides functions to decode Postgres logical replication messages in Python.
All messages come in as raw bytes, and we parse them according to the official
Postgres logical decoding protocol.

For each message type (Begin, Commit, Insert, Update, Delete, Relation, Truncate,
and Logical Message), we extract the pertinent fields.
"""

import struct
import datetime

def decode_message(payload: bytes) -> dict:
    """
    Decodes the raw replication 'payload' bytes into a Python dict
    representing Postgres logical replication messages.

    Returns a dict with 'type' and other fields depending on the message.
    """
    if not payload:
        return {"type": "empty_or_unsupported", "raw": payload}

    # The first byte indicates the WAL message type (B, C, I, U, D, R, T, M, etc.)
    msg_type = payload[0:1]  # single byte
    body = payload[1:]       # rest of the payload

    if msg_type == b'B':  # BEGIN
        return decode_begin(body)
    elif msg_type == b'C':  # COMMIT
        return decode_commit(body)
    elif msg_type == b'I':  # INSERT
        return decode_insert(body)
    elif msg_type == b'U':  # UPDATE
        return decode_update(body)
    elif msg_type == b'D':  # DELETE
        return decode_delete(body)
    elif msg_type == b'R':  # RELATION
        return decode_relation(body)
    elif msg_type == b'T':  # TRUNCATE
        return decode_truncate(body)
    elif msg_type == b'M':  # LOGICAL MESSAGE
        return decode_logical_message(body)
    else:
        return {"type": "unsupported", "raw": payload.hex()}

def decode_begin(body: bytes) -> dict:
    """
    Postgres replication BEGIN message structure:

    - 8 bytes: final LSN (big-endian)
    - 8 bytes: commit timestamp (microseconds since 2000-01-01)
    - 4 bytes: xid
    """
    if len(body) < 20:
        return {"type": "begin", "error": "payload too small", "raw": body.hex()}

    final_lsn_bytes = body[0:8]
    commit_timestamp_bytes = body[8:16]
    xid_bytes = body[16:20]

    final_lsn = decode_lsn(final_lsn_bytes)
    commit_timestamp = pgtimestamp_to_datetime(
        struct.unpack('!Q', commit_timestamp_bytes)[0]
    )
    xid = struct.unpack('!I', xid_bytes)[0]

    return {
        "type": "begin",
        "final_lsn": final_lsn,
        "commit_timestamp": commit_timestamp,
        "xid": xid
    }

def decode_commit(body: bytes) -> dict:
    """
    Postgres replication COMMIT message structure:

    - 1 byte: flags
    - 8 bytes: commit LSN
    - 8 bytes: end LSN
    - 8 bytes: commit timestamp
    """
    if len(body) < 25:
        return {"type": "commit", "error": "payload too small", "raw": body.hex()}

    flags = body[0]
    commit_lsn_bytes = body[1:9]
    end_lsn_bytes = body[9:17]
    commit_timestamp_bytes = body[17:25]

    commit_lsn = decode_lsn(commit_lsn_bytes)
    end_lsn = decode_lsn(end_lsn_bytes)
    commit_timestamp = pgtimestamp_to_datetime(
        struct.unpack('!Q', commit_timestamp_bytes)[0]
    )

    return {
        "type": "commit",
        "flags": flags,
        "lsn": commit_lsn,
        "end_lsn": end_lsn,
        "commit_timestamp": commit_timestamp
    }

def decode_insert(body: bytes) -> dict:
    """
    Postgres replication INSERT message structure:

    - 4 bytes: relation ID
    - 1 byte: tag (often 'N' for 'new tuple')
    - 2 bytes: number_of_columns
    - rest: raw tuple data
    """
    if len(body) < 7:
        return {"type": "insert", "error": "payload too small", "raw": body.hex()}

    relation_id = struct.unpack('!I', body[0:4])[0]
    tag = body[4:5]  # 'N' or other
    number_of_columns = struct.unpack('!H', body[5:7])[0]
    tuple_data = body[7:]

    return {
        "type": "insert",
        "relation_id": relation_id,
        "tag": tag.decode(errors='ignore'),
        "columns": number_of_columns,
        "tuple_raw": tuple_data.hex(),
    }

def decode_update(body: bytes) -> dict:
    """
    Postgres replication UPDATE message structure:

    - 4 bytes: relation ID
    - Then possible tags: 'K' (changed key), 'O' (old), 'N' (new), etc.
    - Each chunk has columns, raw tuple data, etc.
    """
    if len(body) < 5:
        return {"type": "update", "error": "payload too small", "raw": body.hex()}

    relation_id = struct.unpack('!I', body[0:4])[0]
    rest = body[4:]  # could parse further (tags, old_tuple_data, new_tuple_data, etc.)

    return {
        "type": "update",
        "relation_id": relation_id,
        "raw": rest.hex(),
    }

def decode_delete(body: bytes) -> dict:
    """
    Postgres replication DELETE message structure:

    - 4 bytes: relation ID
    - Then either 'K' or 'O' and old tuple data
    """
    if len(body) < 5:
        return {"type": "delete", "error": "payload too small", "raw": body.hex()}

    relation_id = struct.unpack('!I', body[0:4])[0]
    return {
        "type": "delete",
        "relation_id": relation_id,
        "raw": body[4:].hex(),
    }

def decode_relation(body: bytes) -> dict:
    """
    Postgres replication RELATION message structure:

    - 4 bytes: relation ID
    - null-terminated string: namespace (schema name)
    - null-terminated string: relation name (table name)
    - 1 byte: replica identity setting
    - 2 bytes: number of columns
    - For each column:
        - 1 byte: flags
        - null-terminated string: column name
        - 4 bytes: data type OID
        - 4 bytes: type modifier
    """
    if len(body) < 4:
        return {"type": "relation", "error": "payload too small", "raw": body.hex()}

    offset = 0
    relation_id = struct.unpack('!I', body[offset:offset+4])[0]
    offset += 4

    # Read namespace (schema)
    namespace, offset = read_cstring(body, offset)
    # Read relation (table) name
    relname, offset = read_cstring(body, offset)
    # Read replica identity (1 byte)
    if offset >= len(body):
        return {"type": "relation", "error": "incomplete replica identity", "raw": body.hex()}
    replica_identity = body[offset:offset+1].decode(errors='ignore')
    offset += 1

    # Read number of columns (2 bytes)
    if offset + 2 > len(body):
        return {"type": "relation", "error": "incomplete columns count", "raw": body.hex()}
    num_columns = struct.unpack('!H', body[offset:offset+2])[0]
    offset += 2

    columns_meta = []
    columns_names = []
    for _ in range(num_columns):
        if offset >= len(body):
            break  # Incomplete column data
        # Column flag: 1 byte
        col_flag = body[offset:offset+1].decode(errors='ignore')
        offset += 1
        # Column name: null-terminated string
        colname, offset = read_cstring(body, offset)
        # Data type OID: 4 bytes
        if offset + 4 > len(body):
            break
        type_oid = struct.unpack('!I', body[offset:offset+4])[0]
        offset += 4
        # Type modifier: 4 bytes (signed integer)
        if offset + 4 > len(body):
            break
        type_mod = struct.unpack('!i', body[offset:offset+4])[0]
        offset += 4

        columns_names.append(colname)
        columns_meta.append({
            "flag": col_flag,
            "name": colname,
            "type_oid": type_oid,
            "type_mod": type_mod,
        })

    return {
        "type": "relation",
        "relation_id": relation_id,
        "namespace": namespace,
        "relation_name": relname,
        "replica_identity": replica_identity,
        "columns": columns_names,       # List of column names for convenience.
        "columns_meta": columns_meta,   # Full metadata for each column.
        "raw": body.hex()
    }

def decode_truncate(body: bytes) -> dict:
    """
    Postgres replication TRUNCATE message structure:

    - 4 bytes: number of relations
    - 1 byte: options
    - then repeated relation IDs
    """
    if len(body) < 4:
        return {"type": "truncate", "error": "payload too small", "raw": body.hex()}

    number_of_relations = struct.unpack('!I', body[0:4])[0]
    return {
        "type": "truncate",
        "number_of_relations": number_of_relations,
        "raw": body[4:].hex(),
    }

def decode_logical_message(body: bytes) -> dict:
    """
    Postgres replication LOGICAL MESSAGE structure:

    - 1 byte: 't' or 'f' for 'transactional'
    - 8 bytes: LSN
    - then prefix (null-terminated), then 4-byte length, then message content
    """
    if len(body) < 10:
        return {"type": "logical_message", "error": "payload too small", "raw": body.hex()}

    transactional = (body[0:1] == b't')
    lsn_bytes = body[1:9]
    lsn = decode_lsn(lsn_bytes)
    rest = body[9:]

    parts = rest.split(b' ', 1)
    if len(parts) < 2:
        return {"type": "logical_message", "error": "missing prefix null byte", "raw": body.hex()}
    prefix = parts[0].decode(errors='ignore')
    content_raw = parts[1]

    if len(content_raw) < 4:
        return {"type": "logical_message", "error": "content too short", "prefix": prefix}

    content_length = struct.unpack('!I', content_raw[0:4])[0]
    content = content_raw[4:4+content_length]

    return {
        "type": "logical_message",
        "transactional": transactional,
        "lsn": lsn,
        "prefix": prefix,
        "content": content.decode(errors='ignore'),
    }

def decode_lsn(lsn_bytes: bytes):
    """
    Decodes 8 bytes into a Postgres LSN (log sequence number).
    Interpreted as two 32-bit unsigned integers (big-endian).
    """
    if len(lsn_bytes) < 8:
        return None
    (xlog_file, xlog_offset) = struct.unpack('!II', lsn_bytes)
    return (xlog_file, xlog_offset)

def pgtimestamp_to_datetime(pg_microseconds: int) -> datetime.datetime:
    """
    Postgres replication timestamps are microseconds since 2000-01-01 00:00:00 UTC.
    We add that offset to produce a Python datetime.
    """
    pg_epoch = datetime.datetime(2000, 1, 1, tzinfo=datetime.timezone.utc)
    delta = datetime.timedelta(microseconds=pg_microseconds)
    return pg_epoch + delta

def read_cstring(data: bytes, offset: int) -> (str, int):
    """
    Reads a null-terminated string from data starting at offset.
    Returns a tuple of (decoded_string, new_offset).
    """
    end = data.find(b' ', offset)
    if end == -1:
        # No null terminator found; return the remainder
        return data[offset:].decode('utf-8', errors='replace'), len(data)
    s = data[offset:end].decode('utf-8', errors='replace')
    return s, end + 1
