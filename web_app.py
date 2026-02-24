"""
Flask web app to display project details from QR code scan.
"""

from flask import Flask, render_template, request
import sqlite3
import os
from urllib.parse import urlparse, parse_qs

app = Flask(__name__, static_folder='qr_codes', static_url_path='/qr_codes')

DATABASE = "expo.db"


# -----------------------------
# Helper: Get Project By ID
# -----------------------------
def get_project_by_id(project_id):
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                id,
                name,
                roll,
                project_title,
                project_description,
                website_link,
                video_link,
                qr_path
            FROM projects
            WHERE id = ?
            """,
            (project_id,),
        )
        data = cursor.fetchone()
        conn.close()
        return data
    except Exception as e:
        print("Database Error:", e)
        return None


# -----------------------------
# Helper: Get All Projects
# -----------------------------
def get_all_projects():
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                id,
                name,
                roll,
                project_title,
                project_description,
                website_link,
                video_link,
                qr_path
            FROM projects
            """
        )
        data = cursor.fetchall()
        conn.close()
        return data
    except Exception as e:
        print("Database Error:", e)
        return []


def get_youtube_embed_url(url):
    """Return YouTube embed URL if *url* is YouTube, else None."""
    if not url:
        return None

    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    path = parsed.path or ""
    video_id = None

    if "youtu.be" in host:
        video_id = path.strip("/")
    elif "youtube.com" in host:
        if path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [None])[0]
        elif path.startswith("/shorts/"):
            video_id = path.split("/shorts/", 1)[1].split("/", 1)[0]
        elif path.startswith("/embed/"):
            video_id = path.split("/embed/", 1)[1].split("/", 1)[0]

    if not video_id:
        return None

    return (
        f"https://www.youtube.com/embed/{video_id}"
        f"?autoplay=1&mute=1&playsinline=1&rel=0&modestbranding=1"
    )


def get_video_context(video_link, website):
    """
    Resolve best render strategy:
    - direct mp4/webm/ogg in <video>
    - YouTube in <iframe>
    - fallback to website if that is a YouTube URL
    """
    candidate = (video_link or "").strip()
    website = (website or "").strip()

    if not candidate and website:
        candidate = website

    youtube_embed = get_youtube_embed_url(candidate)
    if youtube_embed:
        return {
            "video_mode": "youtube",
            "video_src": youtube_embed,
        }

    lower = candidate.lower()
    if lower.endswith((".mp4", ".webm", ".ogg")):
        return {
            "video_mode": "direct",
            "video_src": candidate,
        }

    return {
        "video_mode": None,
        "video_src": "",
    }


# -----------------------------
# Main Route
# -----------------------------
@app.route("/")
def index():
    project_id = request.args.get("id")

    # If QR scanned (with ?id=)
    if project_id:

        project_data = get_project_by_id(project_id)

        if project_data:
            website = project_data[5]
            description = project_data[4]
            video_link = project_data[6]
            video = get_video_context(video_link, website)

            return render_template(
                "project_detail.html",
                name=project_data[1],
                roll=project_data[2],
                project_title=project_data[3],
                website=website,
                description=description,
                video_mode=video["video_mode"],
                video_src=video["video_src"],
            )
        else:
            return render_template("project_not_found.html")

    # If no ID → show all projects
    projects_raw = get_all_projects()
    projects = []

    for row in projects_raw:
        projects.append({
            "id": row[0],
            "name": row[1],
            "roll": row[2],
            "title": row[3],
            "website": row[5],
            "description": row[4],
            "video_link": row[6],
        })

    return render_template("projects_list.html", projects=projects)


# -----------------------------
# Run Server
# -----------------------------
if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "5000"))
    app.run(host=host, port=port, debug=False)
