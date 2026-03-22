import sqlite3
from fastapi import FastAPI, HTTPException

app = FastAPI()

# ---------- Database Setup ----------
def init_db():
    with sqlite3.connect("messages.db") as conn:
        cursor = conn.cursor()
        # Users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT DEFAULT 'Unknown',
            mobile TEXT UNIQUE NOT NULL
        )
        """)
        # Messages table with sender_mobile
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            sender_mobile TEXT NOT NULL,
            message TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """)
        conn.commit()
    print("Database initialized successfully!")


# ---------- Helper Functions ----------
def get_or_create_user(mobile: str, name: str = "Unknown"):
    with sqlite3.connect("messages.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM users WHERE mobile = ?", (mobile,))
        user = cursor.fetchone()
        if user:
            user_id, current_name = user
            if name and current_name == "Unknown":
                cursor.execute("UPDATE users SET name = ? WHERE id = ?", (name, user_id))
                conn.commit()
            return user_id
        else:
            cursor.execute("INSERT INTO users (mobile, name) VALUES (?, ?)", (mobile, name))
            conn.commit()
            return cursor.lastrowid

def update_user_name(mobile: str, new_name: str):
    with sqlite3.connect("messages.db") as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET name = ? WHERE mobile = ?", (new_name, mobile))
        conn.commit()
        return cursor.rowcount > 0

def save_message(user_id: int, message: str, sender_mobile: str):
    with sqlite3.connect("messages.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (user_id, sender_mobile, message) VALUES (?, ?, ?)",
            (user_id, sender_mobile, message)
        )
        conn.commit()


def get_last_message(mobile: str):
    """
    Returns the last message for the given receiver mobile along with sender.
    """
    with sqlite3.connect("messages.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.sender_mobile, m.message 
            FROM messages m
            JOIN users u ON m.user_id = u.id
            WHERE u.mobile = ?
            ORDER BY m.id DESC
            LIMIT 1
        """, (mobile,))
        result = cursor.fetchone()
        if result:
            sender_mobile, message = result
            return {"sender_mobile": sender_mobile, "message": message}
        else:
            return None


def get_all_message(receiver_mobile: str, sender_mobile: str = None):
    with sqlite3.connect("messages.db") as conn:
        cursor = conn.cursor()
        query = """
            SELECT sender_mobile, message FROM messages m
            JOIN users u ON m.user_id = u.id
            WHERE u.mobile = ?
        """
        params = [receiver_mobile]

        if sender_mobile:
            query += " AND m.sender_mobile = ?"
            params.append(sender_mobile)

        query += " ORDER BY m.id ASC"
        cursor.execute(query, params)
        results = cursor.fetchall()
        return [{"sender_mobile": row[0], "message": row[1]} for row in results] if results else []


# ---------- FastAPI Endpoints ----------
@app.post("/create_data")
def create_data(request: dict):
    mobile = request.get("mobile")           # receiver mobile
    sender_mobile = request.get("sender_mobile")  # sender mobile
    name = request.get("name") or "Unknown"
    message = request.get("message") or ""

    user_id = get_or_create_user(mobile, name)
    save_message(user_id, message, sender_mobile)

    return {
        "status": "success",
        "user_id": user_id,
        "receiver_mobile": mobile,
        "sender_mobile": sender_mobile,
        "message": message
    }


@app.post("/update_name")
def update_name(request: dict):
    mobile = request.get("mobile")
    name = request.get("name")
    updated = update_user_name(mobile, name)
    if updated:
        return {"status": "success", "mobile": mobile, "name": name}
    else:
        raise HTTPException(status_code=404, detail="User not found")

@app.post("/last_message")
def last_message(request: dict):
    mobile = request.get("mobile")
    message = get_last_message(mobile)
    if message:
        return {"mobile": mobile, "last_message": message}
    else:
        raise HTTPException(status_code=404, detail="No messages found")

@app.post("/all_message")
def all_message(request: dict):
    mobile = request.get("mobile")
    messages = get_all_message(mobile)
    if messages:
        return {"mobile": mobile, "messages": messages}
    else:
        raise HTTPException(status_code=404, detail="No messages found")

# Initialize DB
init_db()