from flask import Flask, render_template, request, redirect, session, jsonify, send_file
import sqlite3, random, io
from fpdf import FPDF
from ai_utils import generate_ai_summary, get_video_suggestion, send_emergency_alerts

app = Flask(__name__)
app.secret_key = "vitalsystem"

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
            gender TEXT,
            family_email TEXT,
            family_phone TEXT,
            doctor_email TEXT,
            doctor_phone TEXT
        )
    """)
    # Migration helper: Add columns if they don't exist
    columns = [c[1] for c in cur.execute("PRAGMA table_info(patients)").fetchall()]
    if "family_email" not in columns:
        cur.execute("ALTER TABLE patients ADD COLUMN family_email TEXT")
    if "family_phone" not in columns:
        cur.execute("ALTER TABLE patients ADD COLUMN family_phone TEXT")
    if "doctor_email" not in columns:
        cur.execute("ALTER TABLE patients ADD COLUMN doctor_email TEXT")
    if "doctor_phone" not in columns:
        cur.execute("ALTER TABLE patients ADD COLUMN doctor_phone TEXT")
        
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vitals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            heart_rate INTEGER,
            temperature REAL,
            spo2 INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients (id)
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

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT role FROM users WHERE username=? AND password=? AND role=?", (user, pw, role))
        result = cur.fetchone()
        conn.close()

        if result:
            session["role"] = role
            session["username"] = user
            return redirect("/dashboard")

        return "Invalid Login"

    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        user = request.form["username"]
        pw = request.form["password"]
        role = request.form["role"]

        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (user, pw, role))
            conn.commit()
            conn.close()
            return redirect("/")
        except sqlite3.IntegrityError:
            return "Username already exists"

    return render_template("signup.html")


@app.route("/dashboard")
def dashboard():
    if "role" not in session:
        return redirect("/")
    
    user_info = {
        "role": session["role"],
        "name": session.get("username", "User"),
        "greeting": "Good Morning"
    }
    
    return render_template("dashboard_dynamic.html", user=user_info)


@app.route("/add_patient", methods=["POST"])
def add_patient():
    if session.get("role") != "hospital":
        return redirect("/dashboard")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO patients (
            name, age, gender, 
            family_email, family_phone, 
            doctor_email, doctor_phone
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        request.form["name"], 
        request.form["age"], 
        request.form["gender"],
        request.form.get("family_email", ""),
        request.form.get("family_phone", ""),
        request.form.get("doctor_email", ""),
        request.form.get("doctor_phone", "")
    ))
    conn.commit()
    conn.close()
    return redirect("/dashboard")


@app.route("/delete_patient/<int:pid>")
def delete_patient(pid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM patients WHERE id=?", (pid,))
    cur.execute("DELETE FROM vitals WHERE patient_id=?", (pid,))
    conn.commit()
    conn.close()
    return redirect("/dashboard")


@app.route("/get_patients")
def get_patients():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, age, gender FROM patients")
    rows = cur.fetchall()
    
    patients = []
    for r in rows:
        pid = r[0]
        cur.execute("SELECT heart_rate, temperature, spo2 FROM vitals WHERE patient_id=? ORDER BY id DESC LIMIT 1", (pid,))
        vital = cur.fetchone()
        
        if vital:
            hr, temp, spo2 = vital
        else:
            hr, temp, spo2 = 0, 0, 0

        # Detection logic
        status = "Normal"
        danger = False
        if hr < 60 or hr > 100 or temp > 38 or spo2 < 94:
            status = "Critical"
            danger = True
        elif hr > 90 or temp > 37.5 or spo2 < 96:
            status = "Warning"


        patients.append({
            "id": pid,
            "name": r[1],
            "age": r[2],
            "gender": r[3],
            "Pulse": hr,
            "Temperature": temp,
            "SpO2": spo2,
            "status": status,
            "danger": danger,
            "video_url": get_video_suggestion([{"heart_rate": hr, "temperature": temp, "spo2": spo2}]) if (danger or status == "Warning") else None
        })

    conn.close()
    return jsonify(patients)


@app.route("/vitals/<int:pid>")
def get_vitals(pid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT heart_rate, temperature, spo2, timestamp FROM vitals WHERE patient_id=? ORDER BY id DESC LIMIT 20", (pid,))
    rows = cur.fetchall()
    conn.close()
    
    vitals = [{"heart_rate": r[0], "temperature": r[1], "spo2": r[2], "timestamp": r[3]} for r in reversed(rows)]
    return jsonify(vitals)


@app.route("/vitals", methods=["POST"])
def post_vitals():
    data = request.json
    pid = data.get("patient_id")
    hr = data.get("heart_rate")
    temp = data.get("temperature")
    spo2 = data.get("spo2")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO vitals (patient_id, heart_rate, temperature, spo2) VALUES (?, ?, ?, ?)", (pid, hr, temp, spo2))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})


@app.route("/simulate_data")
def simulate_data():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM patients")
    pids = [r[0] for r in cur.fetchall()]
    
    for pid in pids:
        hr = random.randint(55, 110)
        temp = round(random.uniform(36.0, 39.0), 1)
        spo2 = random.randint(90, 100)
        cur.execute("INSERT INTO vitals (patient_id, heart_rate, temperature, spo2) VALUES (?, ?, ?, ?)", (pid, hr, temp, spo2))
        
        # Check for Critical Status
        if hr < 60 or hr > 105 or temp > 38.5 or spo2 < 92:
            # Fetch patient details for alert
            p_cur = conn.cursor()
            p_cur.execute("SELECT name, family_email, family_phone, doctor_email, doctor_phone FROM patients WHERE id=?", (pid,))
            p = p_cur.fetchone()
            if p:
                send_emergency_alerts(
                    p[0], 
                    f"HR: {hr}, Temp: {temp}, SpO2: {spo2}",
                    {"email": p[1], "phone": p[2]},
                    {"email": p[3], "phone": p[4]}
                )
    
    conn.commit()
    conn.close()
    return redirect("/dashboard")


@app.route("/get_summary/<int:pid>")
def get_summary(pid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT name FROM patients WHERE id=?", (pid,))
    patient = cur.fetchone()
    if not patient:
        conn.close()
        return "Patient not found", 404
    
    cur.execute("SELECT heart_rate, temperature, spo2, timestamp FROM vitals WHERE patient_id=? ORDER BY id DESC LIMIT 20", (pid,))
    rows = cur.fetchall()
    conn.close()
    
    vitals = [{"heart_rate": r[0], "temperature": r[1], "spo2": r[2], "timestamp": r[3]} for r in rows]
    result = generate_ai_summary(vitals, patient[0])
    return jsonify(result)


@app.route("/download_report/<int:pid>")
def download_report(pid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT name, age, gender FROM patients WHERE id=?", (pid,))
    patient = cur.fetchone()
    if not patient:
        conn.close()
        return "Patient not found", 404
    
    cur.execute("SELECT heart_rate, temperature, spo2, timestamp FROM vitals WHERE patient_id=? ORDER BY id DESC LIMIT 20", (pid,))
    rows = cur.fetchall()
    conn.close()
    
    vitals = [{"heart_rate": r[0], "temperature": r[1], "spo2": r[2], "timestamp": r[3]} for r in rows]
    result = generate_ai_summary(vitals, patient[0])
    summary = result['summary']

    # Generate PDF (Matching User's Reference Layout)
    pdf = FPDF()
    pdf.add_page()
    
    # Title
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, txt="Automated Vital Monitoring System - Medical Report", ln=True, align='C')
    pdf.ln(10)
    
    # Patient Info
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, txt=f"Patient Name: {patient[0]}", ln=True)
    pdf.cell(0, 10, txt=f"Age: {patient[1]} | Gender: {patient[2]}", ln=True)
    pdf.ln(5)
    
    # Section Title
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, txt="AI Health Assessment Summary", ln=True)
    pdf.ln(2)
    
    import io
    # AI Assessment Content
    pdf.set_font("Arial", size=10)
    # Removing incompatible characters and using standard hyphens for bullets
    safe_summary = summary.replace('**', '').replace('###', '').replace('##', '').replace('•', '-').replace('*', '-')
    # Ensure it fits latin-1
    safe_summary = safe_summary.encode('latin-1', 'replace').decode('latin-1')
    
    pdf.multi_cell(0, 10, txt=safe_summary)
    pdf.ln(10)
    
    # ... Table drawing code ...
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, txt="Last 20 Vital Readings Data Table", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(50, 10, "Timestamp", 1, 0, 'L')
    pdf.cell(40, 10, "Heart Rate", 1, 0, 'L')
    pdf.cell(40, 10, "SpO2 %", 1, 0, 'L')
    pdf.cell(40, 10, "Temp C", 1, 1, 'L')
    for v in vitals:
        pdf.cell(50, 10, str(v['timestamp']), 1, 0, 'L')
        pdf.cell(40, 10, f"{v['heart_rate']} bpm", 1, 0, 'L')
        pdf.cell(40, 10, f"{v['spo2']}%", 1, 0, 'L')
        pdf.cell(40, 10, f"{v['temperature']} C", 1, 1, 'L')

    # Serving the PDF safely
    buf = io.BytesIO()
    # output() without arguments returns a string in some fpdf versions, 
    # or writes to a file if a name is given. 
    # Using dest='S' returns a string/bytes depending on version.
    pdf_str = pdf.output(dest='S')
    if isinstance(pdf_str, str):
        buf.write(pdf_str.encode('latin-1'))
    else:
        buf.write(pdf_str)
    buf.seek(0)
    
    return send_file(
        buf,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"Report_{patient[0].replace(' ', '_')}.pdf"
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
