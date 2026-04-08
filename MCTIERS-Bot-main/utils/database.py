import mysql.connector
import logging
import os
import json
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import asyncio

load_dotenv()
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

def _get_db_connection():
    try:
        return mysql.connector.connect(
            pool_name="mypool",
            pool_size=5,
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci"
        )
    except mysql.connector.Error as err:
        logging.error(f"Database connection error: {err}")
        return None

def _db_write_sync(query, params=None):
    conn = _get_db_connection()
    if not conn: return False
    with conn.cursor() as cursor:
        try:
            cursor.execute(query, params)
            conn.commit()
            return True
        except mysql.connector.Error as e:
            logging.error(f"DB Write Error: {e}")
            conn.rollback()
            return False
        finally:
            if conn.is_connected():
                conn.close()

def _db_fetch_one_sync(query, params=None):
    conn = _get_db_connection()
    if not conn: return None
    with conn.cursor(dictionary=True) as cursor:
        try:
            cursor.execute(query, params)
            return cursor.fetchone()
        except mysql.connector.Error as e:
            logging.error(f"DB Fetch One Error: {e}")
            return None
        finally:
            if conn.is_connected():
                conn.close()

def _db_fetch_all_sync(query, params=None):
    conn = _get_db_connection()
    if not conn: return []
    with conn.cursor(dictionary=True) as cursor:
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        except mysql.connector.Error as e:
            logging.error(f"DB Fetch All Error: {e}")
            return []
        finally:
            if conn.is_connected():
                conn.close()

def _load_data_from_json_sync(filename: str, default_data=None):
    fp = os.path.join(DATA_DIR, filename)
    try:
        with open(fp, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default_data if default_data is not None else {}

def _save_data_to_json_sync(filename: str, data):
    fp = os.path.join(DATA_DIR, filename)
    with open(fp, 'w') as f:
        json.dump(data, f, indent=2)

async def db_write(query, params=None):
    return await asyncio.to_thread(_db_write_sync, query, params)

async def db_fetch_one(query, params=None):
    return await asyncio.to_thread(_db_fetch_one_sync, query, params)

async def db_fetch_all(query, params=None):
    return await asyncio.to_thread(_db_fetch_all_sync, query, params)

async def load_data_from_json(filename: str, default_data=None):
    return await asyncio.to_thread(_load_data_from_json_sync, filename, default_data)

async def save_data_to_json(filename: str, data):
    await asyncio.to_thread(_save_data_to_json_sync, filename, data)

async def get_player_data(identifier: int | str, by_uuid=False, by_ign=False):
    column = "p.uuid" if by_uuid else "p.minecraft_username" if by_ign else "p.discord_id"
    query = f"""
        SELECT p.discord_id, p.minecraft_username, p.uuid,
               t.tier, t.peak_tier, t.points, t.region, t.server, t.last_time_tested, t.is_retired
        FROM players p
        LEFT JOIN tiers t ON p.discord_id = t.discord_id
        WHERE {column} = %s
    """
    return await db_fetch_one(query, (identifier,))
    
async def get_master_player_record(identifier: int | str, by_uuid=False, by_ign=False):
    column = "uuid" if by_uuid else "minecraft_username" if by_ign else "discord_id"
    return await db_fetch_one(f"SELECT * FROM players WHERE `{column}` = %s", (identifier,))

async def is_user_verified(discord_id: int):
    return bool(await db_fetch_one("SELECT 1 FROM players WHERE discord_id = %s", (discord_id,)))

async def is_on_cooldown(user_id: int) -> tuple[bool, timedelta | None]:
    cooldown_data = await db_fetch_one("SELECT expires_at FROM cooldowns WHERE discord_id = %s", (user_id,))
    if not cooldown_data or not cooldown_data.get('expires_at'): return False, None
    
    expires_at = cooldown_data['expires_at'].replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    
    if expires_at > now:
        return True, expires_at - now

    await db_write("DELETE FROM cooldowns WHERE discord_id = %s", (user_id,))
    return False, None

async def get_ticket_data(channel_id: int):
    return await db_fetch_one("SELECT * FROM testing_tickets WHERE channel_id = %s", (channel_id,))

async def get_all_tickets():
    return await db_fetch_all("SELECT * FROM testing_tickets")