"""
Flask web server for Relational Algebra Explorer
Run with: python app.py
"""

from flask import Flask, request, jsonify, send_from_directory
import os
import converter
import sql_conector

app = Flask(__name__, static_folder="static", static_url_path="")

# ── serve frontend ──────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


# ── API ─────────────────────────────────────────────────────────────────────

@app.route("/query", methods=["POST"])
def query():
    try:
        body = request.get_json(force=True, silent=True)
        if not body or "query" not in body:
            return jsonify({"error": "Missing 'query' field in request body"}), 400

        raw = body["query"].strip()
        if not raw:
            return jsonify({"error": "Query is empty"}), 400

        # The JS sends π as "?" due to URL encoding workaround — put it back
        raw = raw.replace("?", "π")

        # Convert relational algebra → SQL
        processor = converter.QueryProcessor(raw)
        sql = processor.process()

        # Execute against SQLite — fetch rows AND column names
        import sqlite3
        conn = sqlite3.connect("database.db")
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        columns = [description[0] for description in cur.description] if cur.description else []
        conn.close()

        return jsonify({
            "sql": sql,
            "columns": columns,
            "rows": [list(r) for r in rows]
        })

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Server error: {e}"}), 500


# ── also expose /tables so the UI can list available tables ─────────────────

@app.route("/tables", methods=["GET"])
def tables():
    try:
        rows = sql_conector.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        return jsonify({"tables": [r[0] for r in rows] if rows else []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("=" * 55)
    print("  Relational Algebra Explorer  →  http://127.0.0.1:5000")
    print("=" * 55)
    app.run(debug=True, port=5000)
