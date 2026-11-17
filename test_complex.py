"""
Checks nested / join-heavy queries: each case is converted to SQL, run on
SQLite, and compared with the expected rows.   Run:  python test_complex.py
(creates user_dbs/pets.db first if missing)
"""
import os
import sqlite3
import sys

import converter
import explainer

if not os.path.exists("user_dbs/pets.db"):
    import seed_pets_db  # noqa: F401  (creates the db on import)

PETS = "user_dbs/pets.db"
UNI = "database.db"

CASES = [
    # (db, relational algebra, expected rows as a set, or None = just must run)
    (PETS, "(π Owners.OID,Owners.City (π OID,City (Owners)⨝Owns⨝π PetID (Pets))) ÷ (π City (Pets))",
     set()),                                     # owner city can't cover 3 cities
    (PETS, "π OID, City (Owns ⨝ π PetID, City (Pets)) ÷ π City (Pets)",
     {(1,)}),                                    # Asha owns pets from every city
    (PETS, "π OName (Owners ⨝ Owns ⨝ π PetID (σ Species='Dog' (Pets)))",
     {("Asha",), ("Meena",), ("Ravi",)}),
    (PETS, "π OName, PName (Owners ⨝[Owners.OID = Owns.OID] Owns ⨝[Owns.PetID = Pets.PetID] Pets)",
     None),
    (PETS, "π OName (σ PetID IS NULL (Owners ⟕ Owns))",
     {("Kiran",)}),                              # owners with no pets
    (PETS, "π PName (σ OID IS NULL (Owns ⟖ Pets))",
     {("Goldie",)}),                             # pets with no owner
    (PETS, "π OID (Owners) − π OID (Owns)",
     {(4,)}),
    (PETS, "π City (Owners) ∩ π City (Pets)",
     {("Bhopal",), ("Indore",), ("Pune",)}),
    (PETS, "σ (Species='Dog' ∨ Species='Cat') ∧ City='Indore' (Pets)",
     {(102, "Kitty", "Cat", "Indore"), (104, "Bruno", "Dog", "Indore")}),
    (PETS, "π OName (σ City='Bhopal' (σ OID>1 (Owners)))",
     {("Meena",)}),                              # two σ: both kept
    (PETS, "π P.PName (ρ P (Pets) ⨝[P.City = O.City] ρ O (σ OName='Ravi' (Owners)))",
     {("Kitty",), ("Bruno",)}),
    (PETS, "π OName (Owners) ∪ π PName (Pets) ∪ π City (Pets)",
     None),
    # original university database still works
    (UNI, "π name (students)", None),
    (UNI, "(π student_id, subject_id (result)) ÷ (π subject_id (subject))", None),
    (UNI, "π name (students) ∪ π name (professor)", None),
    (UNI, "ρ prof_info(staff_id, full_name, dept) (π prof_id, name, dept_id (professor))", None),
]

failed = 0
for db, ra, expected in CASES:
    try:
        p = converter.QueryProcessor(ra, db_name=db)
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            sql = p.process()
        rows = set(map(tuple, sqlite3.connect(db).execute(sql).fetchall()))
        ok = expected is None or rows == expected
        status = "PASS" if ok else "FAIL"
    except Exception as e:  # noqa: BLE001
        sql, rows, ok, status = "", str(e), False, "ERROR"
    failed += not ok
    print(f"[{status}] {ra}")
    if not ok:
        print(f"    SQL: {sql}\n    got: {rows}\n    expected: {expected}")
    else:
        print(f"    {explainer.explain(p.tree)}")

print(f"\n{len(CASES) - failed}/{len(CASES)} passed")
sys.exit(1 if failed else 0)
