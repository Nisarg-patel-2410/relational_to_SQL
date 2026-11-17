"""
API robustness sweep: every endpoint gets valid and broken input.
A response is acceptable if it is 200 with data, or 400 with a readable
error message. Any 500 / crash / non-JSON reply is a failure.
Run:  python test_api.py
"""
import contextlib
import io
import sys

import app

client = app.app.test_client()
UNI, PETS = {}, {"X-DB-Name": "pets.db"}
failures = []


def call(method, url, headers=None, **kw):
    with contextlib.redirect_stdout(io.StringIO()):
        r = getattr(client, method)(url, headers=headers or {}, **kw)
    try:
        data = r.get_json()
    except Exception:  # noqa: BLE001
        data = None
    return r.status_code, data


def expect(label, status, data, ok_codes=(200,), want_error=False):
    good = isinstance(data, dict) and status in ok_codes
    if want_error:
        good = good and bool(data.get("error"))
        msg = (data or {}).get("error", "")
        good = good and "Server error" not in msg and "Traceback" not in msg
    if not good:
        failures.append(f"{label}: {status} {str(data)[:200]}")
    print(f"[{'ok ' if good else 'BAD'}] {label}" + ("" if good else f"  -> {status} {str(data)[:160]}"))


# ── valid queries on every endpoint ──
VALID = [
    (UNI, "π name, email (professor)"),
    (UNI, "σ gender='Female' ∧ dept_id=1 (students)"),
    (UNI, "π students.name, subject.subject_name (σ grade='A' (students ⋈ result ⋈ subject))"),
    (UNI, "π student_id, subject_id (result) ÷ π subject_id (σ dept_id=1 (subject))"),
    (UNI, "γ dept_id; COUNT(*)→n (students)"),
    (UNI, "π name (σ mentor.student_id IS NULL (students ⟕[students.student_id = mentor.student_id] mentor))"),
    (UNI, "ρ prof_info(staff_id, full_name, dept) (π prof_id, name, dept_id (professor))"),
    (UNI, "students"),
    (UNI, "(students)"),
    (UNI, "π name (students) ∪ π name (professor) ∩ π name (students)"),
    (UNI, "σ gender = 'Female' (students) − σ dept_id = 1 (students)"),
    (UNI, "π name,email(professor)"),                       # no spaces
    (UNI, "π  name ,  email   ( professor )"),              # extra spaces
    (UNI, "students ⨝ department"),                         # alternate join symbol
    (UNI, "σ name LIKE 'A%' (students)"),
    (UNI, "σ dept_id IN (1, 2) (students)"),
    (UNI, "σ dept_id ≥ 2 (students)"),
    (UNI, "σ ¬(dept_id = 1) (students)"),
    (PETS, "π OID, City (Owns ⨝ π PetID, City (Pets)) ÷ π City (Pets)"),
    (PETS, "Owners ⟗ Owns"),
    (PETS, "σ[PName = 'Kitty' ∨ PName = 'Polly'] (Pets)"),
]
for h, q in VALID:
    for url in ("/query", "/query-tree", "/optimize"):
        s, d = call("post", url, h, json={"query": q})
        expect(f"{url} {q[:55]}", s, d)
    s, d = call("post", "/query", h, json={"query": q})
    if isinstance(d, dict) and not d.get("explanation"):
        failures.append(f"no explanation: {q}")

# ── broken relational algebra: must be a clean 400 ──
BROKEN = [
    "", "   ", "π", "σ", "π name", "π name (", "π name (students", "π name (students))",
    "(students", "students)", "students ⋈", "⋈ students", "× ×", "π name (nosuchtable)",
    "σ nosuchcol = 1 (students)", "π nosuchcol (students)", "σ (students)", "ρ (students)",
    "γ (students)", "γ FOO(x) (students)", "students ÷ students", "π name (students) ÷ π name (students)",
    "σ gender='Female (students)", "students ⋈[ students.dept_id = department.dept_id department",
    "π name (students) ∪", "∪ π name (students)", "π name σ", "π name (students) garbage",
    "DROP TABLE students", "SELECT * FROM", "π name (students); DROP TABLE students",
    "😀", "π name (" + "(" * 50 + "students" + ")" * 50 + ")",
]
for q in BROKEN:
    for url in ("/query", "/query-tree", "/optimize"):
        s, d = call("post", url, UNI, json={"query": q})
        expect(f"{url} broken {q[:40]!r}", s, d, ok_codes=(200, 400), want_error=(s != 200))

# deep nesting is legal and must work
s, d = call("post", "/query", UNI, json={"query": "π name (" + "(" * 50 + "students" + ")" * 50 + ")"})
expect("deeply nested parentheses run", s, d)

# ── malformed request bodies ──
for url in ("/query", "/query-tree", "/optimize", "/sql-to-ra"):
    s, d = call("post", url, UNI, data="not json", content_type="text/plain")
    expect(f"{url} non-JSON body", s, d, ok_codes=(400,), want_error=True)
    s, d = call("post", url, UNI, json={})
    expect(f"{url} empty JSON", s, d, ok_codes=(400,), want_error=True)
    s, d = call("post", url, UNI, json={"query": 5, "sql": 5})
    expect(f"{url} wrong type", s, d, ok_codes=(400,), want_error=True)

# ── SQL → RA ──
SQL_OK = [
    "SELECT s.name, d.dept_name FROM students s JOIN department d ON s.dept_id = d.dept_id WHERE s.gender = 'Female'",
    "select name from students",                                   # lower case
    "SELECT name FROM students;",                                  # trailing ;
    "SELECT DISTINCT dept_id FROM students",
    "SELECT * FROM students WHERE dept_id = 1 ORDER BY name LIMIT 2",
    "(SELECT name FROM students) UNION (SELECT name FROM professor)",
    "SELECT name FROM students UNION ALL SELECT name FROM professor",
]
for sql in SQL_OK:
    s, d = call("post", "/sql-to-ra", UNI, json={"sql": sql})
    expect(f"/sql-to-ra {sql[:55]}", s, d)
    limit_warned = any("LIMIT" in w for w in (d or {}).get("warnings", []))
    if isinstance(d, dict) and d.get("roundTrip", {}).get("match") is False and not limit_warned:
        failures.append(f"round trip mismatch: {sql}")

SQL_BAD = [
    "", "SELECT", "SELECT name", "SELECT name FROM", "DELETE FROM students", "DROP TABLE students",
    "UPDATE students SET name='x'", "SELECT name FROM students WHERE id IN (SELECT 1)",
    "SELECT UPPER(name) FROM students", "SELECT name FROM (SELECT name FROM students)",
    "SELECT name FROM students; DROP TABLE students", "SELECT name FROM nosuch",
    "SELECT 'unterminated FROM students", "SELECT name FROM students WHERE",
]
for sql in SQL_BAD:
    s, d = call("post", "/sql-to-ra", UNI, json={"sql": sql})
    ok = s in (200, 400) and isinstance(d, dict)
    if s == 200 and d.get("roundTrip", {}).get("error") is None and "nosuch" in sql:
        ok = False
    expect(f"/sql-to-ra bad {sql[:45]!r}", s, d, ok_codes=(200, 400), want_error=(s != 200))

# database untouched after hostile input
s, d = call("post", "/query", UNI, json={"query": "students"})
expect("students table still intact", s, d)
if isinstance(d, dict) and len(d.get("rows", [])) == 0:
    failures.append("students table emptied!")

# ── GET endpoints ──
for url in ("/", "/tables", "/databases", "/schema"):
    with contextlib.redirect_stdout(io.StringIO()):
        r = client.get(url, headers=UNI)
    good = r.status_code == 200
    print(f"[{'ok ' if good else 'BAD'}] GET {url}")
    if not good:
        failures.append(f"GET {url}: {r.status_code}")
for url in ("/tables", "/schema"):
    with contextlib.redirect_stdout(io.StringIO()):
        r = client.get(url, headers={"X-DB-Name": "../../etc/passwd"})
    print(f"[{'ok ' if r.status_code < 500 else 'BAD'}] GET {url} path traversal -> {r.status_code}")

print("\n" + ("ALL GOOD" if not failures else f"{len(failures)} FAILURES:\n  " + "\n  ".join(failures)))
sys.exit(1 if failures else 0)
