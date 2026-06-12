import aiosqlite
from datetime import datetime

DB_FILE = "/opt/bots/numerium_bot/data/database.db"


async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            created_at TEXT
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS user_balance (
            user_id INTEGER PRIMARY KEY,
            spreads INTEGER DEFAULT 0
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS spreads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            spread_type TEXT,
            question TEXT,
            input_data TEXT,
            answer TEXT,
            created_at TEXT
        )
        """)


        await db.execute("""
        CREATE TABLE IF NOT EXISTS user_limits (
            user_id INTEGER PRIMARY KEY,
            free_spread_used INTEGER DEFAULT 0,
            paid_spreads INTEGER DEFAULT 0
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            payment_id TEXT PRIMARY KEY,
            user_id INTEGER,
            amount REAL,
            spreads_added INTEGER,
            created_at TEXT
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS processed_payments (
            payment_id TEXT PRIMARY KEY,
            user_id INTEGER,
            count INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        await db.commit()


async def ensure_payments_table():
    await init_db()


async def save_user(user):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
        INSERT OR IGNORE INTO users
        (user_id, username, first_name, created_at)
        VALUES (?, ?, ?, ?)
        """, (
            user.id,
            user.username,
            user.first_name,
            datetime.now().isoformat()
        ))
        await db.commit()


async def save_spread(user_id, spread_type, question, input_data, answer):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
        INSERT INTO spreads
        (user_id, spread_type, question, input_data, answer, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            spread_type,
            question,
            input_data,
            answer,
            datetime.now().isoformat()
        ))
        await db.commit()


async def get_user_spreads(user_id, limit=5):
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
        SELECT id, spread_type, question, input_data, answer, created_at
        FROM spreads
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
        """, (user_id, limit))
        rows = await cursor.fetchall()

    return [
        {
            "id": row[0],
            "spread_type": row[1],
            "question": row[2],
            "input_data": row[3],
            "answer": row[4],
            "created_at": row[5]
        }
        for row in rows
    ]


async def get_users_count():
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        row = await cursor.fetchone()
    return row[0]


async def get_spreads_count():
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM spreads")
        row = await cursor.fetchone()
    return row[0]


async def get_recent_spreads(limit=10):
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
        SELECT
            spreads.id,
            spreads.user_id,
            users.username,
            users.first_name,
            spreads.spread_type,
            spreads.question,
            spreads.input_data,
            spreads.created_at
        FROM spreads
        LEFT JOIN users ON users.user_id = spreads.user_id
        ORDER BY spreads.id DESC
        LIMIT ?
        """, (limit,))
        rows = await cursor.fetchall()

    return [
        {
            "id": row[0],
            "user_id": row[1],
            "username": row[2],
            "first_name": row[3],
            "spread_type": row[4],
            "question": row[5],
            "input_data": row[6],
            "created_at": row[7]
        }
        for row in rows
    ]


async def get_recent_users(limit=10):
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
        SELECT user_id, username, first_name, created_at
        FROM users
        ORDER BY created_at DESC
        LIMIT ?
        """, (limit,))
        rows = await cursor.fetchall()

    return [
        {
            "user_id": row[0],
            "username": row[1],
            "first_name": row[2],
            "created_at": row[3]
        }
        for row in rows
    ]


async def can_use_free_spread(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
        SELECT free_spread_used
        FROM user_limits
        WHERE user_id = ?
        """, (user_id,))
        row = await cursor.fetchone()

    if row is None:
        return True

    return row[0] == 0


async def mark_free_spread_used(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
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
        await db.commit()


async def get_spread_type_stats():
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
        SELECT spread_type, COUNT(*) as count
        FROM spreads
        GROUP BY spread_type
        ORDER BY count DESC
        """)
        rows = await cursor.fetchall()

    return [{"spread_type": row[0], "count": row[1]} for row in rows]


async def get_all_user_ids():
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
        SELECT user_id
        FROM users
        ORDER BY created_at ASC
        """)
        rows = await cursor.fetchall()

    return [row[0] for row in rows]


async def get_balance(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(
            "SELECT spreads FROM user_balance WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()

    return row[0] if row else 0


async def add_balance(user_id, amount):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
        INSERT OR IGNORE INTO user_balance(user_id, spreads)
        VALUES (?, 0)
        """, (user_id,))

        await db.execute("""
        UPDATE user_balance
        SET spreads = spreads + ?
        WHERE user_id = ?
        """, (amount, user_id))

        await db.commit()


async def spend_balance(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
        UPDATE user_balance
        SET spreads = spreads - 1
        WHERE user_id = ?
          AND spreads > 0
        """, (user_id,))
        await db.commit()


async def save_payment(payment_id, user_id, amount, spreads_added):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
        INSERT OR IGNORE INTO payments
        (payment_id, user_id, amount, spreads_added, created_at)
        VALUES (?, ?, ?, ?, ?)
        """, (
            payment_id,
            user_id,
            amount,
            spreads_added,
            datetime.now().isoformat()
        ))
        await db.commit()


async def get_top_users(limit=10):
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
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
        top_payers = await cursor.fetchall()

        cursor = await db.execute("""
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
        top_spreads = await cursor.fetchall()

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


async def get_sales_funnel():
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        users_count = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(DISTINCT user_id) FROM spreads")
        analysis_users = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM spreads")
        analyses_count = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(DISTINCT user_id) FROM payments")
        paying_users = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM payments")
        payments_count = (await cursor.fetchone())[0]

    conversion_to_analysis = round((analysis_users / users_count * 100), 1) if users_count else 0
    conversion_to_payment = round((paying_users / users_count * 100), 1) if users_count else 0

    return {
        "users_count": users_count,
        "analysis_users": analysis_users,
        "analyses_count": analyses_count,
        "paying_users": paying_users,
        "payments_count": payments_count,
        "conversion_to_analysis": conversion_to_analysis,
        "conversion_to_payment": conversion_to_payment,
    }


async def get_recent_payments(limit=10):
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
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
        rows = await cursor.fetchall()

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


async def get_payments_stats():
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
        SELECT COUNT(*), COALESCE(SUM(amount), 0), COALESCE(SUM(spreads_added), 0)
        FROM payments
        """)
        total_count, total_amount, total_spreads = await cursor.fetchone()

        cursor = await db.execute("""
        SELECT COUNT(*), COALESCE(SUM(amount), 0), COALESCE(SUM(spreads_added), 0)
        FROM payments
        WHERE date(created_at) = date('now', 'localtime')
        """)
        today_count, today_amount, today_spreads = await cursor.fetchone()

    return {
        "total_count": total_count,
        "total_amount": total_amount,
        "total_spreads": total_spreads,
        "today_count": today_count,
        "today_amount": today_amount,
        "today_spreads": today_spreads,
    }
