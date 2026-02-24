import sqlite3

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

    conn.commit()
    conn.close()


def insert_project(name, roll, title, description, link, video, qr_path):
    conn = sqlite3.connect("expo.db")
    c = conn.cursor()

    c.execute("""
        INSERT INTO projects 
        (name, roll, project_title, project_description, website_link, video_link, qr_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, roll, title, description, link, video, qr_path))

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
