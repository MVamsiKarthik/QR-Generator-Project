import sqlite3
from datetime import datetime, timedelta


QR_VALID_DAYS = 150

def init_db():
    conn = sqlite3.connect("expo.db")
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            roll TEXT,
            project_title TEXT,
            project_description TEXT,
            website_link TEXT,
            video_link TEXT,
            qr_path TEXT
        )
    """)
    # ensure video_link column exists for older databases
    c.execute("PRAGMA table_info(projects)")
    cols = [row[1] for row in c.fetchall()]
    if 'video_link' not in cols:
        c.execute("ALTER TABLE projects ADD COLUMN video_link TEXT")
    if "created_at" not in cols:
        c.execute("ALTER TABLE projects ADD COLUMN created_at TEXT")
    if "expires_at" not in cols:
        c.execute("ALTER TABLE projects ADD COLUMN expires_at TEXT")

    conn.commit()
    conn.close()


def insert_project(name, roll, title, description, link, video, qr_path):
    conn = sqlite3.connect("expo.db")
    c = conn.cursor()
    now = datetime.utcnow()
    expires = now + timedelta(days=QR_VALID_DAYS)

    c.execute("""
        INSERT INTO projects 
        (name, roll, project_title, project_description, website_link, video_link, qr_path, created_at, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name,
        roll,
        title,
        description,
        link,
        video,
        qr_path,
        now.isoformat(timespec="seconds"),
        expires.isoformat(timespec="seconds"),
    ))

    project_id = c.lastrowid
    conn.commit()
    conn.close()
    return project_id


def get_all_projects():
    conn = sqlite3.connect("expo.db")
    c = conn.cursor()

    c.execute("SELECT * FROM projects")
    data = c.fetchall()

    conn.close()
    return data
