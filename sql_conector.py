import sqlite3

def connect(database_name: str = "database.db"):
    conn = sqlite3.connect(database_name)
    cur = conn.cursor()
    return cur, conn


def execute(query: str, params=(), database_name="database.db"):
    cur, conn = connect(database_name)
    cur.execute(query, params)
    
    if query.strip().upper().startswith("SELECT"):
        result = cur.fetchall()
        conn.close()
        return result
    else:
        conn.commit()
        conn.close()
        return None


# Example usage
rows = execute("SELECT dept_name FROM department")
print(rows)
