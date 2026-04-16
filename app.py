"""
Flask web server for Relational Algebra Explorer
Run with: python app.py
"""

from flask import Flask, request, jsonify, send_from_directory
import os
import converter
import sql_conector
import shutil
import sqlite3

app = Flask(__name__, static_folder="static", static_url_path="")

# Ensure dbs directory exists
DB_DIR = "user_dbs"
os.makedirs(DB_DIR, exist_ok=True)

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
        db_name = request.headers.get("X-DB-Name", "database.db")
        if db_name != "database.db":
            db_name = os.path.join(DB_DIR, db_name)
            
        processor = converter.QueryProcessor(raw, db_name=db_name)
        sql = processor.process()

        # Execute against SQLite — fetch rows AND column names
        conn = sqlite3.connect(db_name)
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


# ── Expression tree endpoint ─────────────────────────────────────────────────

def _node_label(node) -> str:
    """Return a human-readable label for a tree node."""
    from converter import (TableNode, ProjectionNode, SelectionNode,
                           CrossJoinNode, NaturalJoinNode, UnionNode,
                           IntersectNode, MinusNode, RenameNode, DivisionNode)
    if isinstance(node, TableNode):
        return node.name
    if isinstance(node, ProjectionNode):
        return f"π {', '.join(node.columns)}"
    if isinstance(node, SelectionNode):
        return f"σ {node.condition}"
    if isinstance(node, CrossJoinNode):
        return "× (Cross Join)"
    if isinstance(node, NaturalJoinNode):
        return "⋈ (Natural Join)"
    if isinstance(node, UnionNode):
        return "∪ (Union)"
    if isinstance(node, IntersectNode):
        return "∩ (Intersect)"
    if isinstance(node, MinusNode):
        return "− (Minus)"
    if isinstance(node, DivisionNode):
        return "÷ (Division)"
    if isinstance(node, RenameNode):
        cols = f"({', '.join(node.columns)})" if node.columns else ""
        return f"ρ {node.new_name}{cols}"
    return "?"


def _build_tree_dict(node, db_name: str) -> dict:
    """Recursively build a JSON-serialisable tree with per-node query results."""
    from converter import (TableNode, ProjectionNode, SelectionNode,
                           CrossJoinNode, NaturalJoinNode, UnionNode,
                           IntersectNode, MinusNode, RenameNode, DivisionNode,
                           SQLConverter)

    label = _node_label(node)

    # Execute this sub-query
    try:
        sql = SQLConverter(node, db_name).convert()
        conn = sqlite3.connect(db_name)
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        columns = [d[0] for d in cur.description] if cur.description else []
        conn.close()
        row_count = len(rows)
        preview = [list(r) for r in rows[:5]]   # first 5 rows for hover popup
    except Exception as e:
        sql = ""
        row_count = 0
        columns = []
        preview = []

    result = {
        "label": label,
        "sql": sql,
        "rowCount": row_count,
        "columns": columns,
        "preview": preview,
        "children": []
    }

    # Recurse into children
    if isinstance(node, (ProjectionNode, SelectionNode, RenameNode)):
        child = node.child
        if child:
            result["children"].append(_build_tree_dict(child, db_name))
    elif isinstance(node, (CrossJoinNode, NaturalJoinNode, UnionNode,
                           IntersectNode, MinusNode, DivisionNode)):
        result["children"].append(_build_tree_dict(node.left, db_name))
        result["children"].append(_build_tree_dict(node.right, db_name))

    return result


@app.route("/query-tree", methods=["POST"])
def query_tree():
    try:
        body = request.get_json(force=True, silent=True)
        if not body or "query" not in body:
            return jsonify({"error": "Missing 'query' field"}), 400

        raw = body["query"].strip()
        if not raw:
            return jsonify({"error": "Query is empty"}), 400

        raw = raw.replace("?", "π")

        db_name = request.headers.get("X-DB-Name", "database.db")
        if db_name != "database.db":
            db_name = os.path.join(DB_DIR, db_name)

        processor = converter.QueryProcessor(raw, db_name=db_name)
        sql = processor.process()   # also builds processor.tree
        tree_data = _build_tree_dict(processor.tree, db_name)

        return jsonify({"tree": tree_data, "sql": sql})

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Server error: {e}"}), 500


# ── Schema endpoint ──────────────────────────────────────────────────────────

@app.route("/schema", methods=["GET"])
def schema():
    try:
        db_name = request.headers.get("X-DB-Name", "database.db")
        db_path = db_name if db_name == "database.db" else os.path.join(DB_DIR, db_name)

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in cur.fetchall()]

        result = []
        for tbl in tables:
            cur.execute(f"PRAGMA table_info([{tbl}])")
            cols = [{"name": row[1], "type": row[2].upper() or "TEXT"}
                    for row in cur.fetchall()]
            result.append({"name": tbl, "columns": cols})

        conn.close()
        return jsonify({"tables": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500





# ── also expose /tables so the UI can list available tables ─────────────────

@app.route("/tables", methods=["GET"])
def tables():
    try:
        db_name = request.headers.get("X-DB-Name", "database.db")
        if db_name != "database.db":
            db_path = os.path.join(DB_DIR, db_name)
        else:
            db_path = "database.db"
            
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        rows = cur.fetchall()
        conn.close()
        
        return jsonify({"tables": [r[0] for r in rows] if rows else []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Dynamic DB switching endpoints ──────────────────────────────────────────

@app.route("/databases", methods=["GET"])
def databases():
    try:
        dbs = ["database.db"]
        if os.path.exists(DB_DIR):
            for f in os.listdir(DB_DIR):
                if f.endswith((".db", ".sqlite", ".sqlite3")):
                    dbs.append(f)
        return jsonify({"databases": dbs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/upload-db", methods=["POST"])
def upload_db():
    if "file" not in request.files:
        return jsonify({"error": "No file parameter"}), 400
        
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
        
    if not file.filename.endswith((".db", ".sqlite", ".sqlite3")):
        return jsonify({"error": "Invalid file type. Must be .db or .sqlite"}), 400
        
    filename = file.filename
    save_path = os.path.join(DB_DIR, filename)
    file.save(save_path)
    
    return jsonify({"message": f"Successfully uploaded {filename}", "db_name": filename})


if __name__ == "__main__":
    print("=" * 55)
    print("  Relational Algebra Explorer  →  http://127.0.0.1:5000")
    print("=" * 55)
    app.run(debug=True, port=5000)
