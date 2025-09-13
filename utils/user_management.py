import psycopg
from passlib.context import CryptContext
from datetime import datetime
import uuid
import logging
import json
from .config import Config

# Configure logging
logger = logging.getLogger(__name__)

# Global connection pool, to be initialized by the main application
db_pool = None

def init_user_management(pool):
    """Initializes the user management module with a database connection pool."""
    global db_pool
    db_pool = pool
    logger.info("User management module initialized with database pool.")

# Configure password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_tables():
    """Create users and conversations tables if they don't exist."""
    if not db_pool:
        raise Exception("User management module not initialized. Call init_user_management() first.")
    conn = None
    try:
        with db_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id UUID PRIMARY KEY,
                        username VARCHAR(255) UNIQUE NOT NULL,
                        password_hash VARCHAR(255) NOT NULL
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id UUID PRIMARY KEY,
                        user_id UUID REFERENCES users(id),
                        title VARCHAR(255) NOT NULL,
                        history JSONB,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        title_set BOOLEAN DEFAULT FALSE
                    );
                """)
                logger.info("Tables 'users' and 'conversations' created or already exist.")
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        raise

def hash_password(password: str) -> str:
    """Hashes a password using bcrypt."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed one."""
    return pwd_context.verify(plain_password, hashed_password)

def register_user(username, password):
    """Registers a new user in the database."""
    if not username or not password:
        return "Username and password are required."

    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cur.fetchone():
                return "Username already exists!"

            user_id = uuid.uuid4()
            password_hash = hash_password(password)

            cur.execute(
                "INSERT INTO users (id, username, password_hash) VALUES (%s, %s, %s)",
                (user_id, username, password_hash)
            )
            return "Registration successful! Please close the popup and log in."

def login_user(username, password):
    """Logs in a user and creates a new conversation."""
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, password_hash FROM users WHERE username = %s", (username,))
            user_record = cur.fetchone()

            if user_record and verify_password(password, user_record[1]):
                user_id = user_record[0]
                # On login, we don't create a new conversation anymore, we just return the latest one.
                # The UI will handle creating a new one if needed.
                cur.execute("SELECT id FROM conversations WHERE user_id = %s ORDER BY created_at DESC LIMIT 1", (user_id,))
                latest_conv = cur.fetchone()
                if latest_conv:
                    conversation_id = latest_conv[0]
                else:
                    # Create a new conversation if the user has none
                    conversation_id = create_new_conversation(user_id)

                return True, username, str(user_id), str(conversation_id), "Login successful!"
            else:
                return False, None, None, None, "Invalid username or password."

def create_new_conversation(user_id, title="New Chat"):
    """Creates a new conversation for a user."""
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            conversation_id = uuid.uuid4()
            cur.execute(
                "INSERT INTO conversations (id, user_id, title, history) VALUES (%s, %s, %s, %s)",
                (conversation_id, user_id, title, '[]')
            )
            return conversation_id

def get_conversation_list_for_user(user_id):
    """Retrieves the list of conversations for a given user."""
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, created_at FROM conversations WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,)
            )
            conversations = cur.fetchall()
            return [{"id": str(row[0]), "title": row[1], "created_at": row[2].strftime("%Y-%m-%d %H:%M:%S")} for row in conversations]

def load_conversation_history(conversation_id):
    """Loads the chat history for a specific conversation."""
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT history FROM conversations WHERE id = %s", (conversation_id,))
            history_record = cur.fetchone()
            return history_record[0] if history_record else []

def update_conversation_history(conversation_id, history):
    """Updates the chat history for a specific conversation."""
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE conversations SET history = %s WHERE id = %s",
                (json.dumps(history), conversation_id)
            )

def update_conversation_title(conversation_id, title):
    """Updates the title of a conversation and marks title_set as True."""
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE conversations SET title = %s, title_set = %s WHERE id = %s AND title_set = %s",
                (title, True, conversation_id, False)
            )
