import sqlite3
from datetime import datetime, date

DB_FILE = "/opt/bots/numerium_bot/data/database.db"


def get_connection():
    return sqlite3.connect(DB_FILE)



def ensure_payments_table():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        payment_id TEXT PRIMARY KEY,
        user_id INTEGER,
        amount REAL,
        spreads_added INTEGER,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        created_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        card_name TEXT,
        orientation TEXT,
        interpretation TEXT,
        created_date TEXT,
        created_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_balance (
        user_id INTEGER PRIMARY KEY,
        spreads INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS spreads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        spread_type TEXT,
        question TEXT,
        cards TEXT,
        answer TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()


def save_user(user):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR IGNORE INTO users
    (user_id, username, first_name, created_at)
    VALUES (?, ?, ?, ?)
    """, (
        user.id,
        user.username,
        user.first_name,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()


def get_today_card(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    today = date.today().isoformat()

    cursor.execute("""
    SELECT card_name, orientation, interpretation
    FROM daily_cards
    WHERE user_id = ?
    AND created_date = ?
    LIMIT 1
    """, (user_id, today))

    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "name": row[0],
            "orientation": row[1],
            "interpretation": row[2]
        }

    return None


def save_daily_card(user_id, card, interpretation):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO daily_cards
    (
        user_id,
        card_name,
        orientation,
        interpretation,
        created_date,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        card["name"],
        card["orientation"],
        interpretation,
        date.today().isoformat(),
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()


def save_spread(user_id, spread_type, question, cards, answer):
    conn = get_connection()
    cursor = conn.cursor()

    cards_text = "; ".join(
        [
            f"{card['name']} ({card['orientation']})"
            for card in cards
        ]
    )

    cursor.execute("""
    INSERT INTO spreads
    (
        user_id,
        spread_type,
        question,
        cards,
        answer,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        spread_type,
        question,
        cards_text,
        answer,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()


def get_user_spreads(user_id, limit=5):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        id,
        spread_type,
        question,
        cards,
        answer,
        created_at
    FROM spreads
    WHERE user_id = ?
    ORDER BY id DESC
    LIMIT ?
    """, (user_id, limit))

    rows = cursor.fetchall()
    conn.close()

    result = []

    for row in rows:
        result.append({
            "id": row[0],
            "spread_type": row[1],
            "question": row[2],
            "cards": row[3],
            "answer": row[4],
            "created_at": row[5]
        })

    return result

def get_users_count():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_daily_cards_count():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM daily_cards")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_spreads_count():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM spreads")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_recent_spreads(limit=10):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        spreads.id,
        spreads.user_id,
        users.username,
        users.first_name,
        spreads.spread_type,
        spreads.question,
        spreads.cards,
        spreads.created_at
    FROM spreads
    LEFT JOIN users ON users.user_id = spreads.user_id
    ORDER BY spreads.id DESC
    LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "user_id": row[1],
            "username": row[2],
            "first_name": row[3],
            "spread_type": row[4],
            "question": row[5],
            "cards": row[6],
            "created_at": row[7]
        }
        for row in rows
    ]


def get_recent_users(limit=10):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        user_id,
        username,
        first_name,
        created_at
    FROM users
    ORDER BY created_at DESC
    LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "user_id": row[0],
            "username": row[1],
            "first_name": row[2],
            "created_at": row[3]
        }
        for row in rows
    ]

def can_use_free_spread(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_limits (
        user_id INTEGER PRIMARY KEY,
        free_spread_used INTEGER DEFAULT 0,
        paid_spreads INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    SELECT free_spread_used
    FROM user_limits
    WHERE user_id = ?
    """, (user_id,))

    row = cursor.fetchone()

    conn.commit()
    conn.close()

    if row is None:
        return True

    return row[0] == 0


def mark_free_spread_used(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_limits (
        user_id INTEGER PRIMARY KEY,
        free_spread_used INTEGER DEFAULT 0,
        paid_spreads INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    INSERT OR REPLACE INTO user_limits
    (user_id, free_spread_used, paid_spreads)
    VALUES (
        ?,
        1,
        COALESCE(
            (
                SELECT paid_spreads
                FROM user_limits
                WHERE user_id = ?
            ),
            0
        )
    )
    """, (user_id, user_id))

    conn.commit()
    conn.close()

def get_spread_type_stats():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        spread_type,
        COUNT(*) as count
    FROM spreads
    GROUP BY spread_type
    ORDER BY count DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "spread_type": row[0],
            "count": row[1]
        }
        for row in rows
    ]

def get_all_user_ids():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT user_id
    FROM users
    ORDER BY created_at ASC
    """)

    rows = cursor.fetchall()
    conn.close()

    return [row[0] for row in rows]


def get_balance(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT spreads FROM user_balance WHERE user_id = ?",
        (user_id,)
    )

    row = cursor.fetchone()
    conn.close()

    return row[0] if row else 0


def add_balance(user_id, amount):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR IGNORE INTO user_balance(user_id, spreads)
    VALUES (?, 0)
    """, (user_id,))

    cursor.execute("""
    UPDATE user_balance
    SET spreads = spreads + ?
    WHERE user_id = ?
    """, (amount, user_id))

    conn.commit()
    conn.close()


def spend_balance(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE user_balance
    SET spreads = spreads - 1
    WHERE user_id = ?
      AND spreads > 0
    """, (user_id,))

    conn.commit()
    conn.close()


def save_payment(payment_id, user_id, amount, spreads_added):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        payment_id TEXT PRIMARY KEY,
        user_id INTEGER,
        amount REAL,
        spreads_added INTEGER,
        created_at TEXT
    )
    """)

    cursor.execute("""
    INSERT OR IGNORE INTO payments
    (
        payment_id,
        user_id,
        amount,
        spreads_added,
        created_at
    )
    VALUES (?, ?, ?, ?, ?)
    """, (
        payment_id,
        user_id,
        amount,
        spreads_added,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()

def get_top_users(limit=10):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        payments.user_id,
        users.username,
        users.first_name,
        COUNT(payments.payment_id) as payments_count,
        COALESCE(SUM(payments.amount), 0) as total_amount,
        COALESCE(SUM(payments.spreads_added), 0) as total_spreads
    FROM payments
    LEFT JOIN users ON users.user_id = payments.user_id
    GROUP BY payments.user_id
    ORDER BY total_amount DESC
    LIMIT ?
    """, (limit,))
    top_payers = cursor.fetchall()

    cursor.execute("""
    SELECT
        spreads.user_id,
        users.username,
        users.first_name,
        COUNT(spreads.id) as spreads_count
    FROM spreads
    LEFT JOIN users ON users.user_id = spreads.user_id
    GROUP BY spreads.user_id
    ORDER BY spreads_count DESC
    LIMIT ?
    """, (limit,))
    top_spreads = cursor.fetchall()

    conn.close()

    return {
        "top_payers": [
            {
                "user_id": row[0],
                "username": row[1],
                "first_name": row[2],
                "payments_count": row[3],
                "total_amount": row[4],
                "total_spreads": row[5],
            }
            for row in top_payers
        ],
        "top_spreads": [
            {
                "user_id": row[0],
                "username": row[1],
                "first_name": row[2],
                "spreads_count": row[3],
            }
            for row in top_spreads
        ],
    }

def get_sales_funnel():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    users_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM spreads")
    analysis_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM spreads")
    analyses_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM payments")
    paying_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM payments")
    payments_count = cursor.fetchone()[0]

    conversion_to_analysis = round((analysis_users / users_count * 100), 1) if users_count else 0
    conversion_to_payment = round((paying_users / users_count * 100), 1) if users_count else 0

    conn.close()

    return {
        "users_count": users_count,
        "analysis_users": analysis_users,
        "analyses_count": analyses_count,
        "paying_users": paying_users,
        "payments_count": payments_count,
        "conversion_to_analysis": conversion_to_analysis,
        "conversion_to_payment": conversion_to_payment,
    }

def get_recent_payments(limit=10):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        payment_id TEXT PRIMARY KEY,
        user_id INTEGER,
        amount REAL,
        spreads_added INTEGER,
        created_at TEXT
    )
    """)

    cursor.execute("""
    SELECT
        payments.payment_id,
        payments.user_id,
        users.username,
        users.first_name,
        payments.amount,
        payments.spreads_added,
        payments.created_at
    FROM payments
    LEFT JOIN users ON users.user_id = payments.user_id
    ORDER BY payments.created_at DESC
    LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "payment_id": row[0],
            "user_id": row[1],
            "username": row[2],
            "first_name": row[3],
            "amount": row[4],
            "spreads_added": row[5],
            "created_at": row[6],
        }
        for row in rows
    ]


def get_payments_stats():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        payment_id TEXT PRIMARY KEY,
        user_id INTEGER,
        amount REAL,
        spreads_added INTEGER,
        created_at TEXT
    )
    """)

    cursor.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0), COALESCE(SUM(spreads_added), 0) FROM payments")
    total_count, total_amount, total_spreads = cursor.fetchone()

    cursor.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0), COALESCE(SUM(spreads_added), 0) FROM payments WHERE date(created_at) = date('now', 'localtime')")
    today_count, today_amount, today_spreads = cursor.fetchone()

    conn.close()

    return {
        "total_count": total_count,
        "total_amount": total_amount,
        "total_spreads": total_spreads,
        "today_count": today_count,
        "today_amount": today_amount,
        "today_spreads": today_spreads,
    }
