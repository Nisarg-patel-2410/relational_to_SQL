"""Collect real numbers for the report: optimizer gains, timings, test counts, code size."""
import contextlib, io, json, os, sqlite3, subprocess, sys, time

sys.path.insert(0, os.getcwd())
import converter, cost, optimizer, sql_to_ra, explainer
from ra_printer import to_ra

UNI, PETS = "database.db", "user_dbs/pets.db"
out = {}

def parse(q, db):
    p = converter.QueryProcessor(q, db_name=db)
    with contextlib.redirect_stdout(io.StringIO()):
        sql = p.process()
    return p.tree, sql

OPT = [
    ("Q1", UNI, "π name, subject_name, marks (σ students.student_id = result.student_id ∧ result.subject_id = subject.subject_id ∧ marks >= 90 (students × result × subject))"),
    ("Q2", UNI, "π name, dept_name (σ students.dept_id = department.dept_id ∧ gender='Female' (students × department))"),
    ("Q3", UNI, "π students.name, subject.subject_name (σ grade='A' (students ⋈ result ⋈ subject))"),
    ("Q4", PETS, "π OName (σ Species='Dog' ∧ OName<>'Ravi' (Owners ⨝ Owns ⨝ Pets))"),
    ("Q5", PETS, "σ City='Bhopal' (π City (Owners) ∪ π City (Pets))"),
    ("Q6", PETS, "σ City='Indore' (γ City; COUNT(*)→n (Pets))"),
]
rows = []
for name, db, q in OPT:
    t, sql = parse(q, db)
    t2, steps = optimizer.optimize(t, db)
    sql2 = converter.SQLConverter(t2, db).convert()
    con = sqlite3.connect(db)
    r1 = set(con.execute(sql).fetchall()); r2 = set(con.execute(sql2).fetchall())
    _, c1 = cost.estimate(t, db); _, c2 = cost.estimate(t2, db)
    rows.append(dict(name=name, db=os.path.basename(db), ra=q, opt=to_ra(t2), c1=round(c1, 1), c2=round(c2, 1),
                     saving=round((c1 - c2) / c1 * 100, 1), rules=[s["id"] for s in steps], match=r1 == r2, rows=len(r2)))
out["optimizer"] = rows

# estimate accuracy: estimated vs actual rows for every node of a few queries
acc = []
for q, db in [(OPT[2][2], UNI), ("γ dept_id; COUNT(*)→n (students)", UNI), ("σ gender='Female' (students)", UNI),
              ("students ⋈ result", UNI), ("Owns ⨝ Pets", PETS), ("σ Species='Dog' (Pets)", PETS)]:
    t, sql = parse(q, db)
    info, _ = cost.estimate(t, db)
    actual = len(sqlite3.connect(db).execute(sql).fetchall())
    acc.append(dict(q=q, est=round(info[id(t)]["rows"], 1), actual=actual))
out["estimates"] = acc

# timing: parse + generate, averaged
def timeit(fn, n=200):
    t0 = time.perf_counter()
    for _ in range(n):
        fn()
    return (time.perf_counter() - t0) / n * 1000
tim = []
for label, q, db in [("Projection", "π name, email (professor)", UNI),
                     ("3-way join + σ", OPT[2][2], UNI),
                     ("Division", "π student_id, subject_id (result) ÷ π subject_id (σ dept_id=1 (subject))", UNI),
                     ("γ aggregation", "γ dept_id; COUNT(*)→n (students)", UNI)]:
    ms_conv = timeit(lambda: parse(q, db))
    t, _ = parse(q, db)
    ms_opt = timeit(lambda: optimizer.optimize(t, db), 50)
    ms_cost = timeit(lambda: cost.estimate(t, db), 50)
    tim.append(dict(label=label, convert=round(ms_conv, 2), optimize=round(ms_opt, 2), cost=round(ms_cost, 2)))
sqls = ["SELECT s.name, d.dept_name FROM students s JOIN department d ON s.dept_id = d.dept_id WHERE s.gender = 'Female'",
        "SELECT dept_id, COUNT(*) AS n FROM students GROUP BY dept_id HAVING COUNT(*) > 1"]
for s in sqls:
    tim.append(dict(label="SQL → RA: " + s[:28] + "…", convert=round(timeit(lambda: sql_to_ra.translate(s)), 2), optimize=None, cost=None))
out["timing"] = tim

# SQL → RA examples
ex = []
for db, s in [(UNI, sqls[0]), (UNI, sqls[1]),
              (UNI, "SELECT s.name FROM students s LEFT JOIN mentor m ON s.student_id = m.student_id WHERE m.mentor_id IS NULL"),
              (UNI, "SELECT name FROM students INTERSECT SELECT name FROM professor"),
              (PETS, "SELECT o.OName, p.PName FROM Owners o, Owns w, Pets p WHERE o.OID = w.OID AND w.PetID = p.PetID AND p.Species = 'Dog'")]:
    t, ra, w = sql_to_ra.translate(s)
    gen = converter.SQLConverter(t, db).convert()
    con = sqlite3.connect(db)
    ex.append(dict(sql=s, ra=ra, match=set(con.execute(s).fetchall()) == set(con.execute(gen).fetchall())))
out["sql2ra"] = ex

# translation examples (RA → SQL + English)
tx = []
for q, db in [("π name, email (professor)", UNI), ("σ gender='Female' ∧ dept_id=1 (students)", UNI),
              ("π name (σ mentor.student_id IS NULL (students ⟕[students.student_id = mentor.student_id] mentor))", UNI),
              ("γ dept_id; COUNT(*)→n (students)", UNI),
              ("π OID, City (Owns ⨝ π PetID, City (Pets)) ÷ π City (Pets)", PETS)]:
    t, sql = parse(q, db)
    tx.append(dict(ra=q, sql=sql, en=explainer.explain(t)))
out["translations"] = tx

# tests
tests = {}
for f in ["test_complex.py", "test_features.py", "test_api.py"]:
    r = subprocess.run([sys.executable, "-X", "utf8", f], capture_output=True, text=True, encoding="utf-8")
    tests[f] = dict(code=r.returncode, last=r.stdout.strip().splitlines()[-1],
                    checks=sum(1 for l in r.stdout.splitlines() if l.startswith(("[PASS]", "[ok ]", "[FAIL]", "[BAD]", "[ERROR]"))))
out["tests"] = tests

# code size
loc = {}
for f in ["converter.py", "optimizer.py", "cost.py", "sql_to_ra.py", "explainer.py", "conditions.py", "ra_printer.py",
          "app.py", "static/script.js", "static/style.css", "static/index.html"]:
    loc[f] = sum(1 for _ in open(f, encoding="utf-8"))
out["loc"] = loc
print(json.dumps(out, ensure_ascii=False, indent=1))
json.dump(out, open(os.path.join(os.path.dirname(__file__), "metrics.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
