"""
Flask web server for Relational Algebra Explorer
Run with: python app.py   →   http://127.0.0.1:5000
"""

import functools
import os
import sqlite3

from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

import converter
import cost
import explainer
import optimizer
import sql_to_ra
from ra_printer import to_ra

app = Flask(__name__, static_folder="static", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024      # uploads up to 50 MB

DB_DIR = "user_dbs"
DEFAULT_DB = "database.db"
DB_EXTENSIONS = (".db", ".sqlite", ".sqlite3")
PREVIEW_ROWS = 100
os.makedirs(DB_DIR, exist_ok=True)


# ── helpers ─────────────────────────────────────────────────────────────────

def api(view):
    """Uniform JSON errors: bad input → 400 with a readable message."""
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        try:
            return view(*args, **kwargs)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except sqlite3.Error as e:
            return jsonify({"error": f"Database error: {e}"}), 400
        except RecursionError:
            return jsonify({"error": "The expression is nested too deeply."}), 400
        except Exception as e:  # noqa: BLE001
            app.logger.exception("Unhandled error")
            return jsonify({"error": f"Server error: {e}"}), 500
    return wrapper


def _db_path() -> str:
    """Database chosen in the UI. Only a bare file name is accepted, so the
    path cannot leave user_dbs/, and unknown names are rejected instead of
    letting SQLite create an empty file."""
    raw = request.headers.get("X-DB-Name") or DEFAULT_DB
    name = os.path.basename(raw)
    if name != raw or not name.endswith(DB_EXTENSIONS):
        raise ValueError(f"Invalid database name '{raw}'")
    path = name if name == DEFAULT_DB else os.path.join(DB_DIR, name)
    if not os.path.isfile(path):
        raise ValueError(f"Database '{name}' was not found")
    return path


def _text(key: str, label: str) -> str:
    body = request.get_json(force=True, silent=True)
    if not isinstance(body, dict):
        raise ValueError("Request body must be JSON")
    value = body.get(key)
    if value is None:
        raise ValueError(f"Missing '{key}' field in request body")
    if not isinstance(value, str):
        raise ValueError(f"'{key}' must be text")
    value = value.strip()
    if not value:
        raise ValueError(f"{label} is empty")
    return value


def _connect(db_name: str):
    """Read-only connection: queries can never modify the database."""
    uri = "file:" + os.path.abspath(db_name).replace("\\", "/") + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _run(sql: str, db_name: str):
    """Run one query read-only; returns (columns, rows)."""
    conn = _connect(db_name)
    try:
        cur = conn.execute(sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        return cols, [list(r) for r in cur.fetchall()]
    finally:
        conn.close()


def _as_set(rows):
    return {tuple(r) for r in rows}


def _parse(raw: str, db_name: str):
    processor = converter.QueryProcessor(raw, db_name=db_name)
    sql = processor.process()
    return processor.tree, sql


def _estimate(tree, db_name):
    try:
        info, total = cost.estimate(tree, db_name)
        return info, round(total, 1)
    except Exception:  # noqa: BLE001  (estimates are optional extras)
        return {}, None


# ── expression tree JSON ────────────────────────────────────────────────────

def _node_label(node) -> str:
    c = converter
    if isinstance(node, c.TableNode):
        return node.name
    if isinstance(node, c.ProjectionNode):
        return f"π {', '.join(node.columns)}"
    if isinstance(node, c.SelectionNode):
        return f"σ {node.condition}"
    if isinstance(node, c.CrossJoinNode):
        return "× (Cross Join)"
    if isinstance(node, c.NaturalJoinNode):
        return "⋈ (Natural Join)"
    if isinstance(node, c.ThetaJoinNode):
        return f"⋈ {node.condition}"
    if isinstance(node, c.OuterJoinNode):
        cond = f" {node.condition}" if node.condition else ""
        return f"{node.SYMBOLS[node.kind]} ({node.kind.title()} Outer Join){cond}"
    if isinstance(node, c.UnionNode):
        return "∪ (Union)"
    if isinstance(node, c.IntersectNode):
        return "∩ (Intersect)"
    if isinstance(node, c.MinusNode):
        return "− (Minus)"
    if isinstance(node, c.DivisionNode):
        return "÷ (Division)"
    if isinstance(node, c.RenameNode):
        cols = f"({', '.join(node.columns)})" if node.columns else ""
        return f"ρ {node.new_name}{cols}"
    if isinstance(node, c.GroupNode):
        return f"γ {node.spec()}"
    return "?"


def _children(node):
    if hasattr(node, "left"):
        return [node.left, node.right]
    child = getattr(node, "child", None)
    return [child] if child is not None else []


def _build_tree_dict(node, db_name: str, info: dict = None) -> dict:
    """JSON tree with each node's own SQL, result preview and cost estimate."""
    try:
        sql = converter.SQLConverter(node, db_name).convert()
        columns, rows = _run(sql, db_name)
        row_count, preview = len(rows), rows[:PREVIEW_ROWS]
    except Exception:  # noqa: BLE001  (a sub-tree may not be runnable alone)
        sql, columns, row_count, preview = "", [], 0, []

    est = (info or {}).get(id(node), {})
    return {
        "label": _node_label(node),
        "estRows": round(est["rows"], 1) if est else None,
        "cost": round(est["cost"], 1) if est else None,
        "formula": est.get("formula", ""),
        "sql": sql,
        "rowCount": row_count,
        "columns": columns,
        "preview": preview,
        "children": [_build_tree_dict(ch, db_name, info) for ch in _children(node)],
    }


# ── pages ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


# ── relational algebra → SQL ────────────────────────────────────────────────

@app.route("/query", methods=["POST"])
@api
def query():
    raw = _text("query", "Query")
    db_name = _db_path()
    tree, sql = _parse(raw, db_name)
    columns, rows = _run(sql, db_name)
    return jsonify({
        "sql": sql,
        "explanation": explainer.explain(tree),
        "columns": columns,
        "rows": rows,
    })


@app.route("/query-tree", methods=["POST"])
@api
def query_tree():
    raw = _text("query", "Query")
    db_name = _db_path()
    tree, sql = _parse(raw, db_name)
    info, total = _estimate(tree, db_name)
    return jsonify({"tree": _build_tree_dict(tree, db_name, info), "sql": sql, "totalCost": total})


@app.route("/optimize", methods=["POST"])
@api
def optimize_query():
    raw = _text("query", "Query")
    db_name = _db_path()
    original, original_sql = _parse(raw, db_name)
    _, rows_o = _run(original_sql, db_name)          # surface query errors first

    optimized, steps = optimizer.optimize(original, db_name)
    optimized_sql = converter.SQLConverter(optimized, db_name).convert()
    _, rows_n = _run(optimized_sql, db_name)

    info_o, cost_o = _estimate(original, db_name)
    info_n, cost_n = _estimate(optimized, db_name)
    return jsonify({
        "original": {
            "ra": raw,
            "sql": original_sql,
            "cost": cost_o,
            "tree": _build_tree_dict(original, db_name, info_o),
        },
        "optimized": {
            "ra": to_ra(optimized),
            "sql": optimized_sql,
            "cost": cost_n,
            "tree": _build_tree_dict(optimized, db_name, info_n),
            "explanation": explainer.explain(optimized),
        },
        "steps": steps,
        "resultsMatch": _as_set(rows_o) == _as_set(rows_n),
        "rowCount": len(rows_n),
    })


# ── SQL → relational algebra ────────────────────────────────────────────────

@app.route("/sql-to-ra", methods=["POST"])
@api
def sql_to_ra_endpoint():
    sql = _text("sql", "SQL")
    db_name = _db_path()
    tree, ra, warnings = sql_to_ra.translate(sql)
    generated = converter.SQLConverter(tree, db_name).convert()

    check = {"match": None, "originalRows": None, "raRows": None, "error": None}
    try:
        _, rows_a = _run(sql, db_name)
        _, rows_b = _run(generated, db_name)
        check.update(match=_as_set(rows_a) == _as_set(rows_b),
                     originalRows=len(_as_set(rows_a)), raRows=len(rows_b))
    except sqlite3.Error as e:
        check["error"] = str(e)

    return jsonify({
        "ra": ra,
        "warnings": warnings,
        "explanation": explainer.explain(tree),
        "generatedSql": generated,
        "roundTrip": check,
    })


# ── schema / databases ──────────────────────────────────────────────────────

def _table_names(conn):
    return [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]


@app.route("/schema", methods=["GET"])
@api
def schema():
    conn = _connect(_db_path())
    try:
        result = []
        for tbl in _table_names(conn):
            info = list(conn.execute(f'PRAGMA table_info("{tbl}")'))
            cols = [{"name": row[1], "type": (row[2] or "TEXT").upper(), "pk": bool(row[5])}
                    for row in info]
            fks = [{"table": r[2], "from": r[3], "to": r[4] or r[3]}
                   for r in conn.execute(f'PRAGMA foreign_key_list("{tbl}")')]
            result.append({"name": tbl, "columns": cols, "foreignKeys": fks})
    finally:
        conn.close()
    return jsonify({"tables": result})


@app.route("/tables", methods=["GET"])
@api
def tables():
    conn = _connect(_db_path())
    try:
        return jsonify({"tables": _table_names(conn)})
    finally:
        conn.close()


@app.route("/databases", methods=["GET"])
@api
def databases():
    dbs = [DEFAULT_DB]
    if os.path.isdir(DB_DIR):
        dbs += sorted(f for f in os.listdir(DB_DIR) if f.endswith(DB_EXTENSIONS))
    return jsonify({"databases": dbs})


@app.route("/upload-db", methods=["POST"])
@api
def upload_db():
    file = request.files.get("file")
    if file is None or not file.filename:
        raise ValueError("No file selected")
    filename = secure_filename(file.filename)
    if not filename.endswith(DB_EXTENSIONS) or filename == DEFAULT_DB:
        raise ValueError("Choose a .db, .sqlite or .sqlite3 file (not named database.db)")
    if file.stream.read(16) != b"SQLite format 3\x00":
        raise ValueError("That file is not a SQLite database")
    file.stream.seek(0)
    file.save(os.path.join(DB_DIR, filename))
    return jsonify({"message": f"Uploaded {filename}", "db_name": filename})


if __name__ == "__main__":
    print("=" * 55)
    print("  Relational Algebra Explorer  →  http://127.0.0.1:5000")
    print("=" * 55)
    app.run(debug=True, port=5000)
