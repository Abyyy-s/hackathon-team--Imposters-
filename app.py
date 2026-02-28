from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3, os, json, random, urllib.request, urllib.error
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime, timedelta

app = Flask(__name__, static_folder='static')
CORS(app)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL   = "gemini-3-flash-preview"
DB_PATH        = "lifelink.db"

# ── Gemini helper ─────────────────────────────────────────────────────

def gemini(system, user, history=None, max_tokens=800):
    if not GEMINI_API_KEY:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    contents = []
    if history:
        for m in history[-6:]:
            contents.append({"role": m["role"], "parts": [{"text": m["content"]}]})
    contents.append({"role": "user", "parts": [{"text": user}]})
    payload = json.dumps({
        "system_instruction": {"parts": [{"text": system}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.7}
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"Gemini error: {e}")
        return None

def strip_json(text):
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    return text.strip()

# ── Database ──────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS donors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            blood_type TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            location TEXT,
            age INTEGER,
            last_donated TEXT,
            total_donations INTEGER DEFAULT 0,
            eligible INTEGER DEFAULT 1,
            lat REAL DEFAULT 0,
            lng REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            blood_type TEXT UNIQUE NOT NULL,
            units_available INTEGER DEFAULT 0,
            units_reserved INTEGER DEFAULT 0,
            last_updated TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hospital TEXT NOT NULL,
            patient_name TEXT,
            blood_type TEXT NOT NULL,
            units_needed INTEGER NOT NULL,
            urgency TEXT DEFAULT 'routine',
            condition TEXT,
            status TEXT DEFAULT 'pending',
            ai_recommendation TEXT,
            allocated_units INTEGER DEFAULT 0,
            lat REAL DEFAULT 0,
            lng REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            message TEXT,
            severity TEXT DEFAULT 'info',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Seed inventory
    blood_types = ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]
    for bt in blood_types:
        c.execute("INSERT OR IGNORE INTO inventory (blood_type, units_available) VALUES (?, ?)",
                  (bt, random.randint(5, 40)))

    # Seed donors
    if c.execute("SELECT COUNT(*) FROM donors").fetchone()[0] == 0:
        sample_donors = [
            ("Arjun Sharma",    "O+",  "9876543210", "Bengaluru", 28, "2024-10-15", 5,  12.9716, 77.5946),
            ("Priya Nair",      "A+",  "9876543211", "Bengaluru", 32, "2024-11-20", 8,  12.9352, 77.6245),
            ("Rahul Verma",     "B+",  "9876543212", "Bengaluru", 25, "2024-09-10", 3,  12.9784, 77.6408),
            ("Sneha Reddy",     "O-",  "9876543213", "Bengaluru", 29, "2024-12-01", 12, 12.9121, 77.6446),
            ("Vikram Menon",    "AB+", "9876543214", "Bengaluru", 35, "2024-08-22", 6,  12.9592, 77.6974),
            ("Ananya Iyer",     "A-",  "9876543215", "Bengaluru", 27, "2025-01-10", 2,  12.9279, 77.6271),
            ("Karthik Rao",     "B-",  "9876543216", "Bengaluru", 31, "2024-07-30", 9,  12.9553, 77.5808),
            ("Divya Krishnan",  "AB-", "9876543217", "Bengaluru", 24, "2025-02-01", 1,  12.9866, 77.5993),
        ]
        for d in sample_donors:
            eligible = 1 if (datetime.now() - datetime.strptime(d[5], "%Y-%m-%d")).days >= 90 else 0
            c.execute("""INSERT INTO donors (name,blood_type,phone,location,age,last_donated,total_donations,eligible,lat,lng)
                         VALUES (?,?,?,?,?,?,?,?,?,?)""",
                      (d[0], d[1], d[2], d[3], d[4], d[5], d[6], eligible, d[7], d[8]))

    # Seed sample requests
    if c.execute("SELECT COUNT(*) FROM requests").fetchone()[0] == 0:
        sample_requests = [
            ("Apollo Hospital",  "Raj Kumar",    "O+",  3, "critical", "Accident victim, severe trauma",        "allocated", 12.9716, 77.6099),
            ("Manipal Hospital", "Sita Devi",    "A+",  2, "urgent",   "Post-surgery hemorrhage",               "pending",   12.9352, 77.6245),
            ("Fortis Hospital",  "Ahmed Khan",   "B-",  1, "routine",  "Scheduled surgery",                     "fulfilled", 12.9784, 77.5800),
            ("NIMHANS",          "Lakshmi Bai",  "O-",  4, "critical", "Emergency C-section complication",      "pending",   12.9400, 77.5950),
        ]
        for r in sample_requests:
            c.execute("""INSERT INTO requests (hospital,patient_name,blood_type,units_needed,urgency,condition,status,lat,lng)
                         VALUES (?,?,?,?,?,?,?,?,?)""", r)

    # Seed alerts
    if c.execute("SELECT COUNT(*) FROM alerts").fetchone()[0] == 0:
        sample_alerts = [
            ("emergency", "🚨 CRITICAL: O- blood needed at NIMHANS — 4 units", "critical"),
            ("shortage",  "⚠️ AB- stock critically low — only 3 units remaining", "warning"),
            ("donor",     "✅ New donor registered: Divya Krishnan (AB-)",        "success"),
            ("fulfilled", "✅ Emergency fulfilled: Apollo Hospital received O+ (3 units)", "success"),
            ("shortage",  "⚠️ B- units below threshold — donor activation recommended", "warning"),
        ]
        for a in sample_alerts:
            c.execute("INSERT INTO alerts (type,message,severity) VALUES (?,?,?)", a)

    conn.commit()
    conn.close()

# ── Routes ────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

# Dashboard stats
@app.route('/api/stats')
def stats():
    conn = get_db()
    total_donors     = conn.execute("SELECT COUNT(*) FROM donors").fetchone()[0]
    eligible_donors  = conn.execute("SELECT COUNT(*) FROM donors WHERE eligible=1").fetchone()[0]
    total_units      = conn.execute("SELECT SUM(units_available) FROM inventory").fetchone()[0] or 0
    pending_requests = conn.execute("SELECT COUNT(*) FROM requests WHERE status='pending'").fetchone()[0]
    critical_count   = conn.execute("SELECT COUNT(*) FROM requests WHERE urgency='critical' AND status='pending'").fetchone()[0]
    conn.close()
    return jsonify({
        "total_donors": total_donors,
        "eligible_donors": eligible_donors,
        "total_units": total_units,
        "pending_requests": pending_requests,
        "critical_count": critical_count,
        "lives_saved": 247
    })

# Inventory
@app.route('/api/inventory')
def get_inventory():
    conn = get_db()
    rows = conn.execute("SELECT * FROM inventory ORDER BY blood_type").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/inventory/update', methods=['POST'])
def update_inventory():
    body = request.json or {}
    conn = get_db()
    conn.execute("UPDATE inventory SET units_available=?, last_updated=CURRENT_TIMESTAMP WHERE blood_type=?",
                 (body['units'], body['blood_type']))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

# Donors
@app.route('/api/donors')
def get_donors():
    conn = get_db()
    rows = conn.execute("SELECT * FROM donors ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/donors/register', methods=['POST'])
def register_donor():
    b = request.json or {}
    # Check eligibility based on last donation date
    eligible = 1
    if b.get('last_donated'):
        try:
            days = (datetime.now() - datetime.strptime(b['last_donated'], "%Y-%m-%d")).days
            eligible = 1 if days >= 90 else 0
        except:
            pass
    # Random coordinates near Bengaluru for demo
    lat = 12.9716 + random.uniform(-0.08, 0.08)
    lng = 77.5946 + random.uniform(-0.08, 0.08)
    conn = get_db()
    conn.execute("""INSERT INTO donors (name,blood_type,phone,email,location,age,last_donated,eligible,lat,lng)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                 (b['name'], b['blood_type'], b.get('phone',''), b.get('email',''),
                  b.get('location','Bengaluru'), b.get('age',25), b.get('last_donated',''), eligible, lat, lng))
    conn.commit()
    # Add alert
    conn.execute("INSERT INTO alerts (type,message,severity) VALUES (?,?,?)",
                 ("donor", f"✅ New donor registered: {b['name']} ({b['blood_type']})", "success"))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "eligible": eligible})

# Blood compatibility map — who can DONATE to the needed type
COMPATIBLE_DONORS = {
    "A+":  ["A+", "A-", "O+", "O-"],
    "A-":  ["A-", "O-"],
    "B+":  ["B+", "B-", "O+", "O-"],
    "B-":  ["B-", "O-"],
    "O+":  ["O+", "O-"],
    "O-":  ["O-"],
    "AB+": ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"],
    "AB-": ["A-", "B-", "O-", "AB-"],
}

# Requests
@app.route('/api/requests')
def get_requests():
    conn = get_db()
    rows = conn.execute("SELECT * FROM requests ORDER BY created_at DESC LIMIT 20").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/requests/submit', methods=['POST'])
def submit_request():
    b = request.json or {}
    lat = 12.9716 + random.uniform(-0.06, 0.06)
    lng = 77.5946 + random.uniform(-0.06, 0.06)
    conn = get_db()
    cur = conn.execute("""INSERT INTO requests (hospital,patient_name,blood_type,units_needed,condition,lat,lng)
                          VALUES (?,?,?,?,?,?,?)""",
                       (b['hospital'], b.get('patient_name','Unknown'), b['blood_type'],
                        b['units_needed'], b.get('condition',''), lat, lng))
    req_id = cur.lastrowid
    conn.commit()

    # AI classify
    urgency = "urgent"
    ai_rec  = "Manual review required."
    inv = conn.execute("SELECT units_available FROM inventory WHERE blood_type=?", (b['blood_type'],)).fetchone()
    stock = inv['units_available'] if inv else 0

    system = """You are LifeLink AI, an emergency blood allocation system for Indian hospitals.
Classify the emergency and recommend allocation. Return ONLY raw JSON (no markdown):
{"urgency":"critical|urgent|routine","reason":"one sentence","recommendation":"allocation plan","activate_donors":true|false}"""
    prompt = f"""Hospital: {b['hospital']}
Patient condition: {b.get('condition','Not specified')}
Blood type needed: {b['blood_type']}
Units needed: {b['units_needed']}
Current stock of {b['blood_type']}: {stock} units"""

    result = gemini(system, prompt, max_tokens=400)
    if result:
        try:
            parsed  = json.loads(strip_json(result))
            urgency = parsed.get("urgency", "urgent")
            ai_rec  = parsed.get("recommendation", ai_rec)
        except:
            pass
    else:
        # Fallback classification
        if b.get('condition','').lower() in ['accident','trauma','critical','hemorrhage','surgery']:
            urgency = "critical"
            ai_rec = f"CRITICAL: Immediately allocate {b['units_needed']} units of {b['blood_type']}. Activate compatible donors."
        else:
            urgency = "urgent"
            ai_rec = f"Allocate {b['units_needed']} units of {b['blood_type']} from inventory. Monitor stock levels."

    conn.execute("UPDATE requests SET urgency=?, ai_recommendation=? WHERE id=?", (urgency, ai_rec, req_id))

    # Auto-allocate if stock available
    if stock >= int(b['units_needed']):
        conn.execute("UPDATE inventory SET units_available=units_available-? WHERE blood_type=?",
                     (b['units_needed'], b['blood_type']))
        conn.execute("UPDATE requests SET status='allocated', allocated_units=? WHERE id=?",
                     (b['units_needed'], req_id))
        conn.execute("INSERT INTO alerts (type,message,severity) VALUES (?,?,?)",
                     ("emergency", f"🚨 {urgency.upper()}: {b['hospital']} needs {b['units_needed']} units of {b['blood_type']}", "critical" if urgency=="critical" else "warning"))
        conn.execute("INSERT INTO alerts (type,message,severity) VALUES (?,?,?)",
                     ("fulfilled", f"✅ Allocated {b['units_needed']} units of {b['blood_type']} to {b['hospital']}", "success"))
    else:
        conn.execute("INSERT INTO alerts (type,message,severity) VALUES (?,?,?)",
                     ("emergency", f"🚨 {urgency.upper()}: {b['hospital']} needs {b['units_needed']} units of {b['blood_type']} — LOW STOCK", "critical"))

    conn.commit()
    conn.close()

    # Auto-find compatible eligible donors if critical
    matched_donors = []
    if urgency == "critical":
        conn2 = get_db()
        compatible_types = COMPATIBLE_DONORS.get(b['blood_type'], [b['blood_type']])
        placeholders = ",".join("?" * len(compatible_types))
        donors = conn2.execute(
            f"SELECT id, name, blood_type, phone, location FROM donors WHERE eligible=1 AND blood_type IN ({placeholders}) ORDER BY RANDOM() LIMIT 5",
            compatible_types
        ).fetchall()
        matched_donors = [dict(d) for d in donors]
        # Log automation event
        if matched_donors:
            names = ", ".join([d["name"] for d in matched_donors])
            conn2.execute(
                "INSERT INTO alerts (type, message, severity) VALUES (?,?,?)",
                ("automation", f"🤖 AUTO-ALERT: {len(matched_donors)} donors notified for {b['blood_type']} emergency at {b['hospital']} — {names}", "critical")
            )
            conn2.commit()
        conn2.close()

    return jsonify({
        "ok": True,
        "urgency": urgency,
        "ai_recommendation": ai_rec,
        "request_id": req_id,
        "matched_donors": matched_donors
    })

# Alerts feed
@app.route('/api/alerts')
def get_alerts():
    conn = get_db()
    rows = conn.execute("SELECT * FROM alerts ORDER BY created_at DESC LIMIT 30").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# Map data
@app.route('/api/map')
def get_map():
    conn = get_db()
    donors   = conn.execute("SELECT id,name,blood_type,location,eligible,lat,lng FROM donors").fetchall()
    requests = conn.execute("SELECT id,hospital,blood_type,units_needed,urgency,status,lat,lng FROM requests WHERE status='pending'").fetchall()
    conn.close()
    hospitals = [
        {"name": "Apollo Hospital",   "lat": 12.9716, "lng": 77.6099, "type": "hospital"},
        {"name": "Manipal Hospital",  "lat": 12.9352, "lng": 77.6245, "type": "hospital"},
        {"name": "Fortis Hospital",   "lat": 12.9784, "lng": 77.5800, "type": "hospital"},
        {"name": "NIMHANS",           "lat": 12.9400, "lng": 77.5950, "type": "hospital"},
        {"name": "Victoria Hospital", "lat": 12.9635, "lng": 77.5760, "type": "hospital"},
    ]
    return jsonify({
        "donors":    [dict(d) for d in donors],
        "requests":  [dict(r) for r in requests],
        "hospitals": hospitals
    })

# AI Shortage Prediction
@app.route('/api/ai/predict', methods=['POST'])
def predict():
    conn  = get_db()
    inv   = conn.execute("SELECT * FROM inventory").fetchall()
    reqs  = conn.execute("SELECT blood_type, COUNT(*) as cnt FROM requests WHERE created_at > datetime('now','-7 days') GROUP BY blood_type").fetchall()
    conn.close()

    inv_text  = "\n".join([f"{r['blood_type']}: {r['units_available']} units" for r in inv])
    req_text  = "\n".join([f"{r['blood_type']}: {r['cnt']} requests this week" for r in reqs]) or "No recent requests"

    system = """You are LifeLink AI shortage predictor for an Indian blood bank.
Return ONLY raw JSON array (no markdown):
[{"blood_type":"X+","risk":"critical|high|medium|low","days_until_shortage":N,"recommendation":"action"}]
For all 8 blood types: A+, A-, B+, B-, O+, O-, AB+, AB-"""
    prompt = f"Current inventory:\n{inv_text}\n\nRequest trends this week:\n{req_text}\n\nPredict shortage risk for each blood type."

    result = gemini(system, prompt, max_tokens=600)
    if result:
        try:
            return jsonify({"predictions": json.loads(strip_json(result))})
        except:
            pass

    # Fallback predictions
    fallback = []
    for r in inv:
        units = r['units_available']
        risk  = "critical" if units < 5 else "high" if units < 10 else "medium" if units < 20 else "low"
        days  = max(1, units * 2)
        fallback.append({"blood_type": r['blood_type'], "risk": risk,
                         "days_until_shortage": days, "recommendation": f"{'Urgent donor activation needed' if risk in ['critical','high'] else 'Monitor stock levels'}"})
    return jsonify({"predictions": fallback})

# AI Chat
@app.route('/api/ai/chat', methods=['POST'])
def chat():
    b       = request.json or {}
    history = b.get("history", [])
    msg     = b.get("message", "")

    conn = get_db()
    inv  = conn.execute("SELECT blood_type, units_available FROM inventory").fetchall()
    donors_count  = conn.execute("SELECT COUNT(*) FROM donors WHERE eligible=1").fetchone()[0]
    pending_count = conn.execute("SELECT COUNT(*) FROM requests WHERE status='pending'").fetchone()[0]
    conn.close()

    inv_summary = ", ".join([f"{r['blood_type']}:{r['units_available']}u" for r in inv])

    if not GEMINI_API_KEY:
        return jsonify({"reply": "⚠️ Set your GEMINI_API_KEY to enable AI chat. Get a free key at aistudio.google.com/app/apikey"})

    system = f"""You are LifeLink AI, an intelligent blood bank assistant for Indian hospitals.
Current inventory: {inv_summary}
Eligible donors: {donors_count} | Pending requests: {pending_count}
Be concise (2-3 sentences). Give specific, actionable medical coordination advice."""

    reply = gemini(system, msg, history=history, max_tokens=300)
    return jsonify({"reply": reply or "I'm having trouble connecting. Please try again."})

if __name__ == '__main__':
    init_db()
    print("\n🩸 LifeLink AI — Blood Emergency Response System")
    print(f"{'✅ Gemini AI active!' if GEMINI_API_KEY else '⚠️  No GEMINI_API_KEY — using fallback logic'}")
    print("📌 Open http://localhost:5000\n")
    app.run(debug=True, port=5000)
