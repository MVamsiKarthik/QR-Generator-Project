import csv
import io
import json
import os
import re
import socket
import sqlite3

import streamlit as st

from database import get_all_projects, init_db, insert_project
from utils.qr_generator import generate_qr


def detect_lan_ip():
    """Return this machine LAN IPv4 for same-network mobile access."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def clean_text(value):
    if value is None:
        return ""
    return str(value).strip()


def safe_filename(text):
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", clean_text(text))
    return cleaned.strip("_") or "project"


def is_valid_image_path(path_value):
    path = clean_text(path_value)
    if not path or path.lower() == "path":
        return False
    return os.path.exists(path)


def set_qr_path(project_id, qr_path):
    conn = sqlite3.connect("expo.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE projects SET qr_path = ? WHERE id = ?", (qr_path, project_id))
    conn.commit()
    conn.close()


def create_project_and_qr(name, roll, project_title, project_description, video_link, qr_base_url):
    # Single-link mode: same value in website_link and video_link.
    project_id = insert_project(
        name,
        roll,
        project_title,
        project_description,
        video_link,
        video_link,
        "",
    )

    unique_url = f"{qr_base_url}/?id={project_id}"
    file_name = safe_filename(f"{roll}_{name}_{project_title}_{project_id}")
    qr_label = f"{name} | {roll}"
    qr_path = generate_qr(unique_url, file_name, label=qr_label)
    set_qr_path(project_id, qr_path)
    return project_id, unique_url, qr_path


def get_field(record, candidates):
    for key in candidates:
        if key in record:
            return clean_text(record.get(key))
    return ""


def normalize_record(record):
    return {
        "name": get_field(record, ["name", "student_name", "student"]),
        "roll": get_field(record, ["roll", "roll_number", "id_no"]),
        "project_title": get_field(record, ["project_title", "title", "project"]),
        "project_description": get_field(record, ["project_description", "description", "desc"]),
        "video_link": get_field(record, ["video_link", "video", "link", "url"]),
    }


def validate_record(record):
    return all(
        [
            record["name"],
            record["roll"],
            record["project_title"],
            record["project_description"],
            record["video_link"],
        ]
    )


def parse_uploaded_records(uploaded_file):
    ext = uploaded_file.name.lower().rsplit(".", 1)[-1]

    if ext == "csv":
        text_data = uploaded_file.getvalue().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text_data))
        return [normalize_record(row) for row in reader]

    if ext == "json":
        raw = json.loads(uploaded_file.getvalue().decode("utf-8"))
        if isinstance(raw, dict):
            raw = raw.get("projects", [])
        if not isinstance(raw, list):
            raise ValueError("JSON must be a list or {\"projects\": [...]} format.")
        return [normalize_record(row) for row in raw if isinstance(row, dict)]

    if ext in {"xlsx", "xls"}:
        try:
            import pandas as pd
        except ImportError as exc:
            raise ValueError(
                "Excel import requires pandas and openpyxl. Install: pip install pandas openpyxl"
            ) from exc

        frame = pd.read_excel(uploaded_file).fillna("")
        return [normalize_record(row) for row in frame.to_dict(orient="records")]

    raise ValueError("Unsupported file type. Use CSV, JSON, or XLSX.")


def show_sample_format():
    sample_csv = (
        "name,roll,project_title,project_description,video_link\n"
        "Alice,101,Face Recognition,Detects faces in live stream,https://www.youtube.com/watch?v=abc123\n"
        "Bob,102,QR Attendance,Scan based attendance system,https://example.com/demo.mp4\n"
    )
    st.caption("Required columns: name, roll, project_title, project_description, video_link")
    st.download_button(
        "Download Sample CSV",
        data=sample_csv,
        file_name="project_import_sample.csv",
        mime="text/csv",
    )


# ================= CONFIG =================
FLASK_PORT = os.getenv("FLASK_PORT", "5000")
DEFAULT_LAN_BASE_URL = f"http://{detect_lan_ip()}:{FLASK_PORT}"
FLASK_BASE_URL = os.getenv("FLASK_BASE_URL", DEFAULT_LAN_BASE_URL).rstrip("/")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
QR_BASE_URL = PUBLIC_BASE_URL or FLASK_BASE_URL

# ================= INIT =================
init_db()

st.set_page_config(
    page_title="Expo QR Registration",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    section.main > div.block-container {
        max-width: 100%;
        padding-top: 1rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🎓 Expo Project Registration System")

menu = st.sidebar.selectbox("Menu", ["Register Project", "Bulk Import", "View All Projects"])

# ================= REGISTER PAGE =================
if menu == "Register Project":
    st.header("Project Registration Form")

    with st.form("registration_form"):
        name = st.text_input("Student Name")
        roll = st.text_input("Roll Number")
        project_title = st.text_input("Project Title")
        video_link = st.text_input("Project Video Link (YouTube or direct .mp4)")
        project_description = st.text_area("Project Description")
        submit = st.form_submit_button("Generate QR & Register")

    if submit:
        name = clean_text(name)
        roll = clean_text(roll)
        project_title = clean_text(project_title)
        project_description = clean_text(project_description)
        video_link = clean_text(video_link)

        if all([name, roll, project_title, project_description, video_link]):
            _, unique_url, qr_path = create_project_and_qr(
                name,
                roll,
                project_title,
                project_description,
                video_link,
                QR_BASE_URL,
            )

            st.success("Registration successful.")
            st.subheader("Generated QR Code")
            st.image(qr_path, width=250)
            st.subheader("QR Redirect URL")
            st.write(unique_url)
        else:
            st.error("Please fill all required fields.")

# ================= BULK IMPORT PAGE =================
elif menu == "Bulk Import":
    st.header("Bulk Import Projects")
    st.write("Upload CSV, JSON, or Excel (XLSX) to register multiple projects automatically.")
    show_sample_format()

    uploaded = st.file_uploader("Upload file", type=["csv", "json", "xlsx", "xls"])
    if uploaded:
        try:
            records = parse_uploaded_records(uploaded)
        except Exception as exc:
            st.error(f"Import error: {exc}")
            records = []

        if records:
            total = len(records)
            valid = [r for r in records if validate_record(r)]
            invalid_count = total - len(valid)

            st.write(f"Rows found: {total}")
            st.write(f"Valid rows: {len(valid)}")
            st.write(f"Invalid rows skipped: {invalid_count}")

            if st.button("Import and Generate QR Codes"):
                success_count = 0
                for row in valid:
                    create_project_and_qr(
                        row["name"],
                        row["roll"],
                        row["project_title"],
                        row["project_description"],
                        row["video_link"],
                        QR_BASE_URL,
                    )
                    success_count += 1

                st.success(f"Imported {success_count} projects and generated QR codes.")

# ================= VIEW PAGE =================
elif menu == "View All Projects":
    st.header("Registered Projects")
    data = get_all_projects()

    if data:
        per_row = 6
        for start in range(0, len(data), per_row):
            cols = st.columns(per_row)
            chunk = data[start:start + per_row]

            for idx, row in enumerate(chunk):
                # DB order: id, name, roll, title, description, website, qr_path, video_link
                with cols[idx]:
                    st.markdown(f"**{row[3]}**")
                    st.caption(f"{row[1]} | {row[2]}")

                    if is_valid_image_path(row[6]):
                        st.image(row[6], use_container_width=True)
                    elif clean_text(row[6]):
                        st.caption("QR image missing")

                    video_value = row[7] if len(row) > 7 else row[5]
                    if video_value:
                        st.markdown(f"[Open Link]({video_value})")
    else:
        st.info("No projects registered yet.")
