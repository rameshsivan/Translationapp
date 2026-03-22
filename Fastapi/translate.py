from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from googletrans import Translator
import sqlite3

app = FastAPI(title="Chat Translator with DB Storage")
translator = Translator()

DB_NAME = "messages.db"

# ---------- Database Initialization ----------
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mobile TEXT UNIQUE NOT NULL
            )
        """)
        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sender_mobile TEXT NOT NULL,
                message TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        conn.commit()
    print("Database initialized successfully!")

init_db()



class UserCreate(BaseModel):
    name: str | None = "Unknown"
    mobile: str


@app.post("/create_user")
def create_user(user: UserCreate):
    try:
        with sqlite3.connect("messages.db") as conn:
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO users (name, mobile) VALUES (?, ?)",
                (user.name, user.mobile)
            )
            conn.commit()

            return {
                "status": "User created successfully",
                "user_id": cursor.lastrowid,
                "name": user.name,
                "mobile": user.mobile
            }

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=400,
            detail="Mobile number already exists"
        )

# ---------- Helper Functions ----------
def get_or_create_user(mobile: str) -> int:
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE mobile = ?", (mobile,))
        user = cursor.fetchone()
        if user:
            return user[0]
        cursor.execute("INSERT INTO users (mobile) VALUES (?)", (mobile,))
        conn.commit()
        return cursor.lastrowid

def save_message(user_id: int, sender_mobile: str, message: str):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (user_id, sender_mobile, message) VALUES (?, ?, ?)",
            (user_id, sender_mobile, message)
        )
        conn.commit()

def translate_text(text: str, target_language: str) -> str:
    return translator.translate(text, dest=target_language).text

def process_chat(text: str) -> str:
    # Replace this with real chatbot logic if needed
    return f"Echo: {text}"

def get_last_message(receiver_mobile: str, sender_mobile: str | None = None):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        query = """
            SELECT m.sender_mobile, m.message
            FROM messages m
            JOIN users u ON m.user_id = u.id
            WHERE u.mobile = ?
        """
        params = [receiver_mobile]
        if sender_mobile:
            query += " AND m.sender_mobile = ?"
            params.append(sender_mobile)
        query += " ORDER BY m.id DESC LIMIT 1"
        cursor.execute(query, params)
        result = cursor.fetchone()
        if result:
            return {"sender_mobile": result[0], "message": result[1]}
        return None

def get_all_messages(receiver_mobile: str, sender_mobile: str | None = None):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        query = """
            SELECT m.sender_mobile, m.message
            FROM messages m
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


# ---------- Endpoints ----------

# ---------- Pydantic Models ----------
@app.post("/send_message")
def send_message_endpoint(request: dict):
    receiver_mobile = request.get("receiver_mobile") 
    sender_mobile = request.get("sender_mobile") 
    message = request.get("message") 
    receiver_id = get_or_create_user(receiver_mobile)
    save_message(receiver_id, sender_mobile, message)
    return {
        "status": "Message stored successfully",
        "receiver_mobile": receiver_mobile,
        "sender_mobile": sender_mobile,
        "message": message
    }

class TranslateRequest(BaseModel):
    receiver_mobile: str
    sender_mobile: str | None = None  # optional: translate last message from this sender
    message: str | None = None        # optional: translate provided message
    translated_to: str = "en"         # target language


@app.post("/chat_message_translate")
def chat_message_translate_endpoint(request: dict):
    receiver_mobile = request.get("receiver_mobile")
    sender_mobile = request.get("sender_mobile")
    message = request.get("message")
    translated_to = request.get("translated_to", "en")  # default to English

    try:
        if message:
            # Translate provided message
            sender = sender_mobile or "unknown"
        else:
            # Translate last stored message
            last = get_last_message(receiver_mobile, sender_mobile)
            if not last:
                raise HTTPException(status_code=404, detail="No messages found")
            sender = last["sender_mobile"]
            message = last["message"]

        detected_lang = translator.detect(message).lang
        translated_to_english = translate_text(message, "en")
        processed_response = process_chat(translated_to_english)
        translated_back = translate_text(processed_response, translated_to)

        return {
            "receiver_mobile": receiver_mobile,
            "sender_mobile": sender,
            "original_message": message,
            "detected_language": detected_lang,
            "target_language": translated_to,
            "translated_to_english": translated_to_english,
            "response_in_target_language": translated_back
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/users")
def get_users():
    conn = sqlite3.connect("messages.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    data = cursor.fetchall()
    conn.close()
    return {"users": data}


@app.post("/messages")
def get_messages():
    conn = sqlite3.connect("messages.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM messages")
    data = cursor.fetchall()
    conn.close()
    return {"messages": data}


# ---------- Run App ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
