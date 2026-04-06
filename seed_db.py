"""
Seed database.db with sample data matching the schema described in database_design.txt:
  Dean → Department → Professor (HOD) / Students → Mentor / Subjects → Results
"""

import sqlite3

conn = sqlite3.connect("database.db")
cur = conn.cursor()

# ── Drop existing tables (clean slate) ──────────────────────────────────────
TABLES = ["result", "subject", "mentor", "students", "professor", "department", "dean"]
for t in TABLES:
    cur.execute(f"DROP TABLE IF EXISTS {t}")

# ── Create tables ────────────────────────────────────────────────────────────

cur.execute("""
CREATE TABLE dean (
    dean_id   INTEGER PRIMARY KEY,
    name      TEXT NOT NULL,
    email     TEXT UNIQUE,
    phone     TEXT
)
""")

cur.execute("""
CREATE TABLE department (
    dept_id   INTEGER PRIMARY KEY,
    dept_name TEXT NOT NULL,
    dean_id   INTEGER REFERENCES dean(dean_id)
)
""")

cur.execute("""
CREATE TABLE professor (
    prof_id   INTEGER PRIMARY KEY,
    name      TEXT NOT NULL,
    email     TEXT UNIQUE,
    gender    TEXT,
    dept_id   INTEGER REFERENCES department(dept_id),
    is_hod    INTEGER DEFAULT 0   -- 1 = HOD
)
""")

cur.execute("""
CREATE TABLE students (
    student_id TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    gender     TEXT,
    dept_id    INTEGER REFERENCES department(dept_id),
    mentor_id  TEXT   -- self-reference via mentor table
)
""")

cur.execute("""
CREATE TABLE mentor (
    mentor_id  TEXT PRIMARY KEY,   -- a student who is also a mentor
    student_id TEXT REFERENCES students(student_id)
)
""")

cur.execute("""
CREATE TABLE subject (
    subject_id   TEXT PRIMARY KEY,
    subject_name TEXT NOT NULL,
    dept_id      INTEGER REFERENCES department(dept_id),
    prof_id      INTEGER REFERENCES professor(prof_id)
)
""")

cur.execute("""
CREATE TABLE result (
    result_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT REFERENCES students(student_id),
    subject_id TEXT REFERENCES subject(subject_id),
    marks      INTEGER,
    total_marks INTEGER DEFAULT 100,
    pass_marks  INTEGER DEFAULT 40,
    grade      TEXT
)
""")

# ── Seed data ─────────────────────────────────────────────────────────────────

# Dean
cur.executemany("INSERT INTO dean VALUES (?,?,?,?)", [
    (1, "Dr. Ramesh Shah",  "ramesh.shah@uni.edu",  "9000000001"),
    (2, "Dr. Priya Mehta",  "priya.mehta@uni.edu",  "9000000002"),
])

# Department
cur.executemany("INSERT INTO department VALUES (?,?,?)", [
    (1, "Computer Science", 1),
    (2, "Information Technology", 2),
    (3, "Electronics", 1),
])

# Professors
cur.executemany("INSERT INTO professor VALUES (?,?,?,?,?,?)", [
    (1,  "Dr. Anita Patel",   "anita.patel@uni.edu",   "Female", 1, 1),
    (2,  "Prof. Raj Kumar",   "raj.kumar@uni.edu",     "Male",   1, 0),
    (3,  "Dr. Sneha Joshi",   "sneha.joshi@uni.edu",   "Female", 2, 1),
    (4,  "Prof. Amit Verma",  "amit.verma@uni.edu",    "Male",   2, 0),
    (5,  "Dr. Neha Singh",    "neha.singh@uni.edu",    "Female", 3, 1),
])

# Students
cur.executemany("INSERT INTO students VALUES (?,?,?,?,?)", [
    ("S001", "Nisarg Patel",   "Male",   1, "M001"),
    ("S002", "Priya Shah",     "Female", 1, "M001"),
    ("S003", "Ravi Mehta",     "Male",   1, "M002"),
    ("S004", "Anjali Desai",   "Female", 2, "M002"),
    ("S005", "Deepak Sharma",  "Male",   2, "M001"),
    ("S006", "Kavya Nair",     "Female", 3, None),
    ("S007", "Arjun Rao",      "Male",   3, None),
    ("S008", "Meera Iyer",     "Female", 1, "M002"),
])

# Mentors (students who mentor others)
cur.executemany("INSERT INTO mentor VALUES (?,?)", [
    ("M001", "S001"),
    ("M002", "S003"),
])

# Subjects
cur.executemany("INSERT INTO subject VALUES (?,?,?,?)", [
    ("SUB01", "Data Structures",       1, 2),
    ("SUB02", "Database Management",   1, 1),
    ("SUB03", "Operating Systems",     1, 2),
    ("SUB04", "Web Technologies",      2, 3),
    ("SUB05", "Computer Networks",     2, 4),
    ("SUB06", "Digital Electronics",   3, 5),
])

# Results  (student_id, subject_id, marks, total, pass, grade)
results_data = [
    ("S001","SUB01", 88, 100, 40, "A"),
    ("S001","SUB02", 76, 100, 40, "B"),
    ("S001","SUB03", 92, 100, 40, "A"),
    ("S002","SUB01", 65, 100, 40, "B"),
    ("S002","SUB02", 90, 100, 40, "A"),
    ("S002","SUB03", 45, 100, 40, "C"),
    ("S003","SUB01", 55, 100, 40, "C"),
    ("S003","SUB02", 38, 100, 40, "F"),
    ("S004","SUB04", 80, 100, 40, "A"),
    ("S004","SUB05", 70, 100, 40, "B"),
    ("S005","SUB04", 60, 100, 40, "B"),
    ("S005","SUB05", 88, 100, 40, "A"),
    ("S006","SUB06", 95, 100, 40, "A"),
    ("S007","SUB06", 72, 100, 40, "B"),
    ("S008","SUB01", 85, 100, 40, "A"),
    ("S008","SUB02", 91, 100, 40, "A"),
]
cur.executemany(
    "INSERT INTO result(student_id,subject_id,marks,total_marks,pass_marks,grade) VALUES (?,?,?,?,?,?)",
    results_data
)

conn.commit()
conn.close()

print("Database seeded successfully!")
print("Tables created: dean, department, professor, students, mentor, subject, result")
