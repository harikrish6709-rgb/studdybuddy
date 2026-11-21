"""Saves chat history in a small SQLite file next to the app."""
import os
import sqlite3
import time
from contextlib import closing

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_history.db")


def _run(sql, args=(), fetch=False):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.execute(sql, args)
        rows = cur.fetchall() if fetch else cur.lastrowid
        conn.commit()
    return rows


def init():
    _run("CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY AUTOINCREMENT, "
         "title TEXT, created REAL)")
    _run("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, "
         "chat_id INTEGER, role TEXT, content TEXT)")


def new_chat(title: str) -> int:
    return _run("INSERT INTO chats (title, created) VALUES (?, ?)",
                (title.strip()[:50] or "New chat", time.time()))


def add_message(chat_id: int, role: str, content: str):
    _run("INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)",
         (chat_id, role, content))


def list_chats(limit: int = 30):
    return _run("SELECT id, title FROM chats ORDER BY id DESC LIMIT ?", (limit,), fetch=True)


def load_messages(chat_id: int):
    return _run("SELECT role, content FROM messages WHERE chat_id = ? ORDER BY id",
                (chat_id,), fetch=True)


def delete_chat(chat_id: int):
    _run("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
    _run("DELETE FROM chats WHERE id = ?", (chat_id,))
