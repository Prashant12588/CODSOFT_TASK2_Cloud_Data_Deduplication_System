from flask import Flask, render_template, request
import pandas as pd
import hashlib

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_file():
    file = request.files.get("file")

    if not file or file.filename == "":
        return render_template(
            "index.html",
            error="No file selected. Please upload a CSV file."
        )

    if not file.filename.lower().endswith(".csv"):
        return render_template(
            "index.html",
            error="Invalid file type. Please upload only CSV files."
        )

    try:
        df = pd.read_csv(file)
    except Exception:
        return render_template(
            "index.html",
            error="Could not read CSV file. Please upload a valid CSV."
        )

    if df.empty:
        return render_template(
            "index.html",
            error="CSV file is empty."
        )

    unique_rows = []
    duplicate_rows = []
    hashes = set()

    for _, row in df.iterrows():
        row_string = "|".join(map(str, row.values))
        row_hash = hashlib.sha256(row_string.encode()).hexdigest()

        if row_hash in hashes:
            duplicate_rows.append(row)
        else:
            hashes.add(row_hash)
            unique_rows.append(row)

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
        unique_table=unique_df.to_html(classes="data-table", index=False),
        duplicate_table=duplicate_df.to_html(classes="data-table", index=False)
    )


if __name__ == "__main__":
    app.run(debug=True)
