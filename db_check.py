import sqlite3
conn = sqlite3.connect("patients.db")
cur = conn.cursor()
cur.execute("SELECT name, family_email, doctor_email FROM patients ORDER BY id DESC LIMIT 5")
for row in cur.fetchall():
    print(row)
conn.close()
