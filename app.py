from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3, random

app = Flask(__name__)
app.secret_key = "vitalsystem"

HOSPITAL_USERS = {"doctor": "hospital123"}
FAMILY_USERS = {"family": {"password": "home123"}}

def get_db():
    return sqlite3.connect("patients.db")

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            age INTEGER,
            gender TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = request.form["role"]
        user = request.form["username"]
        pw = request.form["password"]

        if role == "hospital" and HOSPITAL_USERS.get(user) == pw:
            session["role"] = "hospital"
            return redirect("/dashboard")

        if role == "family" and FAMILY_USERS.get(user, {}).get("password") == pw:
            session["role"] = "family"
            return redirect("/dashboard")

        return "Invalid Login"

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "role" not in session:
        return redirect("/")
    
    # Get user info based on role
    user_info = {
        "role": session["role"],
        "name": "Dr. John Doe" if session["role"] == "hospital" else "Family Member",
        "greeting": "Good Morning"
    }
    
    return render_template("dashboard_dynamic.html", user=user_info)


@app.route("/add_patient", methods=["POST"])
def add_patient():
    if session.get("role") != "hospital":
        return redirect("/dashboard")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO patients (name, age, gender) VALUES (?, ?, ?)",
                (request.form["name"], request.form["age"], request.form["gender"]))
    conn.commit()
    conn.close()
    return redirect("/dashboard")


@app.route("/delete_patient/<int:pid>")
def delete_patient(pid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM patients WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    return redirect("/dashboard")


@app.route("/get_patients")
def get_patients():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, age, gender FROM patients")
    rows = cur.fetchall()
    conn.close()

    patients = []
    for r in rows:
        Pulse = random.randint(55, 130)
        SpO2 = random.randint(85, 100)
        Temp = round(random.uniform(34.0, 40.0), 1)
        danger = Pulse < 60 or Pulse > 110 or SpO2 < 90 or Temp < 35 or Temp > 38

        patients.append({
            "id": r[0],
            "name": r[1],
            "age": r[2],
            "gender": r[3],
            "Pulse": Pulse,
            "SpO2": SpO2,
            "Temperature": Temp,
            "danger": danger
        })

    return jsonify(patients)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
