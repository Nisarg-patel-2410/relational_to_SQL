import sqlite3

def view_all_tables(database_name="database.db"):
    # Connect to the database
    conn = sqlite3.connect(database_name)
    cur = conn.cursor()

    # Get list of tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cur.fetchall()

    if not tables:
        print("No tables found in the database.")
        conn.close()
        return

    print("Tables in the database:")
    for table in tables:
        table_name = table[0]
        print(f"\n--- Table: {table_name} ---")

        # Get column names
        cur.execute(f"PRAGMA table_info({table_name})")
        columns = cur.fetchall()
        column_names = [col[1] for col in columns]
        print("Columns:", ", ".join(column_names))

        # Get all rows from the table
        cur.execute(f"SELECT * FROM {table_name}")
        rows = cur.fetchall()

        if rows:
            print("Data:")
            for row in rows:
                print(row)
        else:
            print("No data in this table.")

    conn.close()

if __name__ == "__main__":
    view_all_tables()