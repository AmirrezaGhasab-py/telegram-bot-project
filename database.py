import aiosqlite
import logging
from datetime import datetime
import secrets
from config import USERS_DB_NAME

def _normalize_phone_number(phone_number: str) -> str:
    if phone_number.startswith('+98'):
        return '0' + phone_number[3:]
    return phone_number

def _row_to_dict(cursor: aiosqlite.Cursor, row: aiosqlite.Row | None) -> dict | None:
    if row:
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))
    return None

async def _generate_unique_referral_code(db: aiosqlite.Connection) -> str:
    while True:
        referral_code = secrets.token_urlsafe(6)
        cursor = await db.execute("SELECT telegram_id FROM customers WHERE referral_code = ?", (referral_code,))
        if await cursor.fetchone() is None:
            return referral_code

async def create_table():
    async with aiosqlite.connect(USERS_DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                telegram_id INTEGER PRIMARY KEY,
                phone_number TEXT UNIQUE NOT NULL,
                first_name TEXT,
                last_name TEXT,
                national_id TEXT,
                birth_date TEXT,
                gender TEXT,
                referral_code TEXT UNIQUE,
                credit INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                registration_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_verified_at TEXT
            )
        """)
        await db.commit()
        logging.info("Database table 'customers' is ready.")

async def get_user(telegram_id: int):
    async with aiosqlite.connect(USERS_DB_NAME) as db:
        cursor = await db.execute("SELECT * FROM customers WHERE telegram_id = ?", (telegram_id,))
        row = await cursor.fetchone()
        return _row_to_dict(cursor, row)

async def get_user_by_phone(phone_number: str):
    normalized_phone = _normalize_phone_number(phone_number)
    async with aiosqlite.connect(USERS_DB_NAME) as db:
        cursor = await db.execute("SELECT * FROM customers WHERE phone_number = ?", (normalized_phone,))
        row = await cursor.fetchone()
        return _row_to_dict(cursor, row)

async def update_user_authentication(phone_number: str, telegram_id: int):
    normalized_phone = _normalize_phone_number(phone_number)
    now_iso = datetime.now().isoformat()
    
    async with aiosqlite.connect(USERS_DB_NAME) as db:
        user = await get_user_by_phone(normalized_phone)
        if not user:
            return

        is_first_auth = not user.get('telegram_id')
        
        if is_first_auth:
            referral_code = user.get('referral_code') or await _generate_unique_referral_code(db)
            await db.execute(
                """UPDATE customers 
                   SET telegram_id = ?, last_verified_at = ?, referral_code = ?, registration_date = ?
                   WHERE phone_number = ?""",
                (telegram_id, now_iso, referral_code, now_iso, normalized_phone)
            )
        else:
            await db.execute(
                "UPDATE customers SET last_verified_at = ? WHERE phone_number = ?",
                (now_iso, normalized_phone)
            )
        await db.commit()
        logging.info(f"User {telegram_id} authenticated. First auth: {is_first_auth}.")

async def add_new_user(
    telegram_id: int, phone_number: str, first_name: str, last_name: str, 
    national_id: str | None, birth_date: str, gender: str
):
    normalized_phone = _normalize_phone_number(phone_number)
    now_iso = datetime.now().isoformat()
    async with aiosqlite.connect(USERS_DB_NAME) as db:
        retry_count = 0
        while retry_count < 5:
            try:
                referral_code = await _generate_unique_referral_code(db)
                await db.execute(
                    """INSERT INTO customers (telegram_id, phone_number, first_name, last_name, national_id, birth_date, gender, last_verified_at, referral_code, registration_date) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (telegram_id, normalized_phone, first_name, last_name, national_id, birth_date, gender, now_iso, referral_code, now_iso)
                )
                await db.commit()
                logging.info(f"New user {telegram_id} registered successfully.")
                return
            except aiosqlite.IntegrityError as e:
                logging.warning(f"IntegrityError on registration for {telegram_id}. Error: {e}")
                existing_user = await get_user_by_phone(normalized_phone)
                if existing_user:
                    logging.error(f"Failed to register user. Phone number {normalized_phone} already exists.")
                    raise ValueError(f"User with phone number {normalized_phone} already exists.")
                
                logging.warning("Retrying with a new referral code...")
                await db.rollback()
                retry_count += 1

async def get_user_by_referral_code(code: str):
    async with aiosqlite.connect(USERS_DB_NAME) as db:
        cursor = await db.execute("SELECT * FROM customers WHERE referral_code = ?", (code,))
        row = await cursor.fetchone()
        return _row_to_dict(cursor, row)

async def add_credit_to_user(telegram_id: int, amount: int):
    async with aiosqlite.connect(USERS_DB_NAME) as db:
        await db.execute("UPDATE customers SET credit = credit + ? WHERE telegram_id = ?", (amount, telegram_id))
        await db.commit()
        logging.info(f"Added {amount} credit to user {telegram_id}.")

async def update_user_details(
    telegram_id: int, first_name: str, last_name: str, 
    national_id: str | None, birth_date: str, gender: str
):
    async with aiosqlite.connect(USERS_DB_NAME) as db:
        await db.execute(
            """UPDATE customers SET 
               first_name = ?, last_name = ?, national_id = ?, birth_date = ?, gender = ?
               WHERE telegram_id = ?""",
            (first_name, last_name, national_id, birth_date, gender, telegram_id)
        )
        await db.commit()
        logging.info(f"User {telegram_id} updated their profile.")