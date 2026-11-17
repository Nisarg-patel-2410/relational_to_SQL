"""
Tests for the optimizer, cost estimator, γ aggregation and SQL → RA.
Every case runs real SQL on SQLite and compares result sets.
Run:  python test_features.py
"""
import contextlib
import io
import os
import sqlite3
import sys

import converter
import cost
import optimizer
import sql_to_ra
from ra_printer import to_ra

if not os.path.exists("user_dbs/pets.db"):
    import seed_pets_db  # noqa: F401

PETS, UNI = "user_dbs/pets.db", "database.db"
passed = failed = 0


def rows(sql, db):
    return set(sqlite3.connect(db).execute(sql).fetchall())


def parse(ra, db):
    p = converter.QueryProcessor(ra, db_name=db)
    with contextlib.redirect_stdout(io.StringIO()):
        sql = p.process()
    return p.tree, sql


def check(name, ok, info=""):
    global passed, failed
    passed += bool(ok)
    failed += not ok
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"\n    {info}" if info and not ok else ""))


# ── 1. Optimizer: same results, never more expensive, expected rules fire ──
OPT = [
    (PETS, "σ Owners.OID = Owns.OID ∧ Owns.PetID = Pets.PetID ∧ Species='Dog' (Owners × Owns × Pets)", {"R1", "R3", "R4"}),
    (PETS, "π OName (σ Species='Dog' ∧ OName<>'Ravi' (Owners ⨝ Owns ⨝ Pets))", {"R1", "R3"}),
    (PETS, "σ City='Bhopal' (π City (Owners) ∪ π City (Pets))", {"R6", "R2"}),
    (PETS, "σ City='Indore' (γ City; COUNT(*)→n (Pets))", {"R7"}),
    (PETS, "π OName (π OName, City (Owners))", {"R8"}),
    (PETS, "σ OID>1 (σ City='Bhopal' (Owners))", {"R9"}),
    (PETS, "σ Owns.PetID IS NULL (Owners ⟕[Owners.OID = Owns.OID] Owns)", set()),   # must NOT push into null side
    (PETS, "σ City='Pune' (Owners ⟕ Owns)", {"R3"}),                                   # preserved side is fine
    (PETS, "σ OID>1 (π OID (Owners) − π OID (Owns))", {"R6"}),
    (UNI, "π name, dept_name (σ students.dept_id = department.dept_id ∧ gender='Female' (students × department))", {"R3", "R4"}),
]
for db, ra, expect in OPT:
    tree, sql = parse(ra, db)
    new, steps = optimizer.optimize(tree, db)
    new_sql = converter.SQLConverter(new, db).convert()
    same = rows(sql, db) == rows(new_sql, db)
    _, c0 = cost.estimate(tree, db)
    _, c1 = cost.estimate(new, db)
    fired = {s["id"] for s in steps}
    ok = same and c1 <= c0 + 1e-9 and expect <= fired and (expect or not fired)
    check(f"optimize {ra[:60]}", ok,
          f"same={same} cost {c0:.1f}->{c1:.1f} rules={sorted(fired)} want⊇{sorted(expect)}\n    {to_ra(new)}")

# ── 2. Cost estimator: textbook formulas on known statistics ──
tree, _ = parse("σ Species='Dog' (Pets)", PETS)          # n=5, V(Species)=4 -> 5/4
info, _ = cost.estimate(tree, PETS)
check("σ A=c  ->  n / V(A)", abs(info[id(tree)]["rows"] - 5 / 4) < 1e-9, info[id(tree)])
tree, _ = parse("Owners × Pets", PETS)                    # 4 x 5
info, _ = cost.estimate(tree, PETS)
check("R × S  ->  n(R)·n(S)", info[id(tree)]["rows"] == 20, info[id(tree)])
tree, _ = parse("Owns ⨝ Pets", PETS)                      # 6*5/max(V(PetID)=4, 5)
info, _ = cost.estimate(tree, PETS)
check("R ⋈ S  ->  n(R)·n(S)/max V", abs(info[id(tree)]["rows"] - 6) < 1e-9, info[id(tree)])
tree, _ = parse("γ Species; COUNT(*)→n (Pets)", PETS)     # V(Species)=4 groups
info, _ = cost.estimate(tree, PETS)
check("γ G  ->  V(G) groups", info[id(tree)]["rows"] == 4, info[id(tree)])
tree, _ = parse("π City (Pets)", PETS)                    # V(City)=3
info, _ = cost.estimate(tree, PETS)
check("π A  ->  min(n, V(A))", info[id(tree)]["rows"] == 3, info[id(tree)])

# ── 3. γ aggregation ──
GAMMA = [
    (UNI, "γ dept_id; COUNT(*)→n (students)", "SELECT dept_id, COUNT(*) FROM students GROUP BY dept_id"),
    (PETS, "γ COUNT(DISTINCT City)→c (Pets)", "SELECT COUNT(DISTINCT City) FROM Pets"),
    (PETS, "σ n>1 (γ City, COUNT(*)→n (Pets))", "SELECT City, COUNT(*) n FROM Pets GROUP BY City HAVING n>1"),
    (PETS, "π OName (σ k=3 (γ OName; COUNT(*)→k (Owners ⨝ Owns)))",
     "SELECT OName FROM Owners NATURAL JOIN Owns GROUP BY OName HAVING COUNT(*)=3"),
]
for db, ra, ref in GAMMA:
    _, sql = parse(ra, db)
    check(f"γ {ra}", rows(sql, db) == rows(ref, db), sql)

# ── 4. SQL → relational algebra, verified by running both ──
S2R = [
    (UNI, "SELECT name FROM students WHERE gender='Female' AND dept_id >= 2"),
    (UNI, "SELECT s.name, d.dept_name FROM students s JOIN department d ON s.dept_id = d.dept_id"),
    (UNI, "SELECT dept_id, COUNT(*) AS n FROM students GROUP BY dept_id HAVING COUNT(*) > 1 ORDER BY n"),
    (UNI, "SELECT name FROM students UNION SELECT name FROM professor"),
    (UNI, "SELECT name FROM students EXCEPT SELECT name FROM professor"),
    (PETS, "SELECT OName FROM Owners LEFT JOIN Owns ON Owners.OID = Owns.OID WHERE Owns.PetID IS NULL"),
    (PETS, "SELECT o.OName, p.PName FROM Owners o, Owns w, Pets p WHERE o.OID = w.OID AND w.PetID = p.PetID"),
    (PETS, "SELECT City, MAX(PName) AS top FROM Pets GROUP BY City"),
    (PETS, "SELECT x.City FROM (SELECT City, COUNT(*) AS n FROM Pets GROUP BY City) AS x WHERE x.n >= 2"),
    (PETS, "SELECT * FROM Owners NATURAL JOIN Owns"),
    (PETS, "SELECT OName AS owner FROM Owners WHERE City = 'Bhopal'"),
    (PETS, "SELECT COUNT(*) FROM Pets"),
    (PETS, "SELECT Species FROM Pets WHERE City IN ('Pune', 'Indore') OR PName LIKE 'G%'"),
    (PETS, "SELECT PName FROM Pets WHERE PetID BETWEEN 102 AND 104"),
]
for db, sql in S2R:
    try:
        tree, ra, _ = sql_to_ra.translate(sql)
        # print → parse again, so the text form is checked too
        tree2, back = parse(ra, db)
        ok = rows(sql, db) == rows(back, db)
        check(f"SQL→RA {sql[:60]}", ok, f"{ra}\n    {back}")
    except Exception as e:  # noqa: BLE001
        check(f"SQL→RA {sql[:60]}", False, repr(e))

try:
    sql_to_ra.translate("SELECT OName FROM Owners WHERE OID IN (SELECT OID FROM Owns)")
    check("SQL→RA rejects WHERE subquery with a message", False)
except ValueError:
    check("SQL→RA rejects WHERE subquery with a message", True)

print(f"\n{passed}/{passed + failed} passed")
sys.exit(1 if failed else 0)
