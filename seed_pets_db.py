"""
Creates user_dbs/pets.db — a small Owners / Owns / Pets database for
trying joins, outer joins and division.  Run:  python seed_pets_db.py

Owners(OID, OName, City)   Pets(PetID, PName, Species, City)   Owns(OID, PetID)

Owner 1 (Asha) owns pets from every city in Pets, so she is the answer to
"owners who own pets from every city":
    π OID, City (Owns ⨝ π PetID, City (Pets)) ÷ π City (Pets)
"""
import os
import sqlite3

os.makedirs("user_dbs", exist_ok=True)
path = os.path.join("user_dbs", "pets.db")
if os.path.exists(path):
    os.remove(path)

con = sqlite3.connect(path)
con.executescript("""
CREATE TABLE Owners (OID INTEGER PRIMARY KEY, OName TEXT, City TEXT);
CREATE TABLE Pets   (PetID INTEGER PRIMARY KEY, PName TEXT, Species TEXT, City TEXT);
CREATE TABLE Owns   (OID INTEGER REFERENCES Owners, PetID INTEGER REFERENCES Pets,
                     PRIMARY KEY (OID, PetID));

INSERT INTO Owners VALUES
  (1, 'Asha',  'Bhopal'),
  (2, 'Ravi',  'Indore'),
  (3, 'Meena', 'Bhopal'),
  (4, 'Kiran', 'Pune');        -- owns no pets

INSERT INTO Pets VALUES
  (101, 'Tommy',  'Dog',    'Bhopal'),
  (102, 'Kitty',  'Cat',    'Indore'),
  (103, 'Polly',  'Parrot', 'Pune'),
  (104, 'Bruno',  'Dog',    'Indore'),
  (105, 'Goldie', 'Fish',   'Bhopal');  -- owned by nobody

INSERT INTO Owns VALUES
  (1, 101), (1, 102), (1, 103),   -- Asha: Bhopal, Indore, Pune
  (2, 102), (2, 104),             -- Ravi: Indore only
  (3, 101);                       -- Meena: Bhopal only
""")
con.commit()
con.close()
print(f"Created {path}")
