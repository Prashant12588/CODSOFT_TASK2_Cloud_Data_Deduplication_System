from flask import Flask, render_template, request
import pandas as pd
import hashlib
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)

DB_PATH = "database/deduplication.db"
os.makedirs("database", exist_ok=True)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_hash TEXT UNIQUE,
            record_data TEXT,
            uploaded_file TEXT,
            uploaded_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS upload_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            total_records INTEGER,
            unique_records INTEGER,
            duplicate_records INTEGER,
            uploaded_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def generate_hash(row):
    ignored_columns = {"id", "student_id", "roll_no", "sr_no", "serial_no"}

    filtered_data = []

    for column, value in row.items():
        if str(column).lower().strip() not in ignored_columns:
            filtered_data.append(str(value).strip().lower())

    row_string = "|".join(filtered_data)
    return hashlib.sha256(row_string.encode()).hexdigest()

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_file():
    file = request.files.get("file")

    if not file or file.filename == "":
        return render_template("index.html", error="No file selected.")

    if not file.filename.lower().endswith(".csv"):
        return render_template("index.html", error="Only CSV files are allowed.")

    try:
        df = pd.read_csv(file)
    except Exception:
        return render_template("index.html", error="Invalid CSV file.")

    if df.empty:
        return render_template("index.html", error="CSV file is empty.")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    unique_rows = []
    duplicate_rows = []

    for _, row in df.iterrows():
        record_hash = generate_hash(row)
        record_data = row.to_json()
        uploaded_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            cursor.execute("""
                INSERT INTO records (record_hash, record_data, uploaded_file, uploaded_at)
                VALUES (?, ?, ?, ?)
            """, (record_hash, record_data, file.filename, uploaded_at))
            unique_rows.append(row)

        except sqlite3.IntegrityError:
            duplicate_rows.append(row)

    cursor.execute("""
        INSERT INTO upload_history
        (filename, total_records, unique_records, duplicate_records, uploaded_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        file.filename,
        len(df),
        len(unique_rows),
        len(duplicate_rows),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()

    unique_df = pd.DataFrame(unique_rows)
    duplicate_df = pd.DataFrame(duplicate_rows)

    stats = {
        "total": len(df),
        "unique": len(unique_df),
        "duplicates": len(duplicate_df)
    }

    return render_template(
        "result.html",
        filename=file.filename,
        stats=stats,
        unique_table=unique_df.to_html(classes="data-table", index=False) if not unique_df.empty else "<p>No new unique records.</p>",
        duplicate_table=duplicate_df.to_html(classes="data-table", index=False) if not duplicate_df.empty else "<p>No duplicate records found.</p>"
    )


@app.route("/history")
def upload_history():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT filename, total_records, unique_records, duplicate_records, uploaded_at
        FROM upload_history
        ORDER BY id DESC
    """)

    history = cursor.fetchall()
    conn.close()

    return render_template("history.html", history=history)

@app.route("/database")
def database_records():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, record_hash, uploaded_file, uploaded_at
        FROM records
        ORDER BY id DESC
    """)

    records = cursor.fetchall()
    conn.close()

    return render_template("database.html", records=records)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
