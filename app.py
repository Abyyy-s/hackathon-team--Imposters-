from flask import Flask, request, jsonify, send_from_directory, make_response
from flask_cors import CORS
import sqlite3, os, json, random, urllib.request, urllib.error
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except (ImportError, ModuleNotFoundError):
    pass

app = Flask(__name__, static_folder='static')   # ✅ CORRECT
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
    except urllib.error.HTTPError as e:
        print(f"Gemini HTTP {e.code}: {e.read().decode()}")
        return None
    except Exception as e:
        print(f"Gemini error: {e}")
        return None

def strip_json(text):
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json\n"):
            text = text[5:]
        elif text.startswith("json"):
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
            ("Arun Kumar",     "O+",  "9447123401", "Ernakulam, Kochi",   28, "2024-10-15", 5,  9.9816,  76.2999),
            ("Priya Menon",    "A+",  "9447123402", "Kakkanad, Kochi",    32, "2024-08-20", 8,  10.0159, 76.3419),
            ("Rahul Nair",     "B+",  "9447123403", "Edappally, Kochi",   25, "2024-09-10", 3,  10.0205, 76.3100),
            ("Sneha Thomas",   "O-",  "9447123404", "Vytilla, Kochi",     29, "2024-08-01", 12, 9.9561,  76.3150),
            ("Vijay Krishnan", "AB+", "9447123405", "Aluva, Kochi",       35, "2024-08-22", 6,  10.0998, 76.3573),
            ("Ananya Jose",    "A-",  "9447123406", "Fort Kochi, Kochi",  27, "2024-09-10", 2,  9.9637,  76.2430),
            ("Kiran Pillai",   "B-",  "9447123407", "Kalamassery, Kochi", 31, "2024-07-30", 9,  10.0524, 76.3141),
            ("Divya Mathew",   "AB-", "9447123408", "Thrikkakara, Kochi", 24, "2024-10-01", 1,  10.0092, 76.3395),
        ]
        for d in sample_donors:
            eligible = 1 if (datetime.now() - datetime.strptime(d[5], "%Y-%m-%d")).days >= 90 else 0
            c.execute("""INSERT INTO donors (name,blood_type,phone,location,age,last_donated,total_donations,eligible,lat,lng)
                         VALUES (?,?,?,?,?,?,?,?,?,?)""",
                      (d[0], d[1], d[2], d[3], d[4], d[5], d[6], eligible, d[7], d[8]))

    # Seed sample requests
    if c.execute("SELECT COUNT(*) FROM requests").fetchone()[0] == 0:
        sample_requests = [
            ("Amrita Institute of Medical Sciences", "Rajan Pillai", "O+",  3, "critical", "Accident victim, severe trauma",   "allocated", 9.9396,  76.3085),
            ("Aster Medcity",                        "Suja Thomas",  "A+",  2, "urgent",   "Post-surgery hemorrhage",          "pending",   9.9553,  76.3127),
            ("Lakeshore Hospital",                   "Suresh Menon", "B-",  1, "routine",  "Scheduled surgery",                "fulfilled", 9.9708,  76.2952),
            ("Ernakulam General Hospital",           "Leela Nair",   "O-",  4, "critical", "Emergency C-section complication", "pending",   9.9843,  76.2767),
        ]
        for r in sample_requests:
            c.execute("""INSERT INTO requests (hospital,patient_name,blood_type,units_needed,urgency,condition,status,lat,lng)
                         VALUES (?,?,?,?,?,?,?,?,?)""", r)

    # Seed alerts
    if c.execute("SELECT COUNT(*) FROM alerts").fetchone()[0] == 0:
        sample_alerts = [
            ("emergency", "🚨 CRITICAL: O- blood needed at Ernakulam General Hospital — 4 units", "critical"),
            ("shortage",  "⚠️ AB- stock critically low — only 3 units remaining", "warning"),
            ("donor",     "✅ New donor registered: Divya Mathew (AB-)", "success"),
            ("fulfilled", "✅ Emergency fulfilled: Amrita AIMS received O+ (3 units)", "success"),
            ("shortage",  "⚠️ B- units below threshold — donor activation recommended", "warning"),
        ]
        for a in sample_alerts:
            c.execute("INSERT INTO alerts (type,message,severity) VALUES (?,?,?)", a)

    conn.commit()
    conn.close()

# ── Routes ────────────────────────────────────────────────────────────

@app.route('/')
def index():
    resp = make_response(send_from_directory('static', 'index.html'))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    return resp

@app.route('/static/<path:filename>')
def static_files(filename):
    resp = make_response(send_from_directory('static', filename))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    return resp

# Dashboard stats
@app.route('/api/stats')
def stats():
    conn = get_db()
    total_donors     = conn.execute("SELECT COUNT(*) FROM donors").fetchone()[0]
    eligible_donors  = conn.execute("SELECT COUNT(*) FROM donors WHERE eligible=1").fetchone()[0]
    total_units      = conn.execute("SELECT SUM(units_available) FROM inventory").fetchone()[0] or 0
    pending_requests = conn.execute("SELECT COUNT(*) FROM requests WHERE status='pending'").fetchone()[0]
    critical_count   = conn.execute("SELECT COUNT(*) FROM requests WHERE urgency='critical' AND status='pending'").fetchone()[0]
    lives_saved      = conn.execute("SELECT COUNT(*) FROM requests WHERE status IN ('allocated','fulfilled')").fetchone()[0]
    conn.close()
    return jsonify({
        "total_donors": total_donors,
        "eligible_donors": eligible_donors,
        "total_units": total_units,
        "pending_requests": pending_requests,
        "critical_count": critical_count,
        "lives_saved": lives_saved
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
    if 'units' not in body or 'blood_type' not in body:
        return jsonify({"ok": False, "error": "Missing units or blood_type"}), 400
    try:
        units = int(body['units'])
        if units < 0: raise ValueError
    except (ValueError, TypeError):
        return jsonify({"ok": False, "error": "units must be a non-negative integer"}), 400
    conn = get_db()
    conn.execute("UPDATE inventory SET units_available=?, last_updated=CURRENT_TIMESTAMP WHERE blood_type=?",
                 (units, body['blood_type']))
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
    # Random coordinates near Kochi for demo
    lat = 9.9312 + random.uniform(-0.08, 0.08)
    lng = 76.2673 + random.uniform(-0.08, 0.08)
    conn = get_db()
    conn.execute("""INSERT INTO donors (name,blood_type,phone,email,location,age,last_donated,eligible,lat,lng)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                 (b['name'], b['blood_type'], b.get('phone',''), b.get('email',''),
                  b.get('location','Kochi'), b.get('age',25), b.get('last_donated',''), eligible, lat, lng))
    conn.commit()
    # Add alert
    conn.execute("INSERT INTO alerts (type,message,severity) VALUES (?,?,?)",
                 ("donor", f"✅ New donor registered: {b['name']} ({b['blood_type']})", "success"))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "eligible": eligible})

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
    # Input validation
    if not b.get('hospital') or not b.get('blood_type') or not b.get('units_needed'):
        return jsonify({"ok": False, "error": "Missing required fields: hospital, blood_type, units_needed"}), 400
    valid_blood_types = ["A+","A-","B+","B-","O+","O-","AB+","AB-"]
    if b['blood_type'] not in valid_blood_types:
        return jsonify({"ok": False, "error": "Invalid blood type"}), 400
    try:
        units = int(b['units_needed'])
        if units < 1: raise ValueError
    except (ValueError, TypeError):
        return jsonify({"ok": False, "error": "units_needed must be a positive integer"}), 400

    lat = 9.9312 + random.uniform(-0.06, 0.06)
    lng = 76.2673 + random.uniform(-0.06, 0.06)
    conn = get_db()
    cur = conn.execute("""INSERT INTO requests (hospital,patient_name,blood_type,units_needed,condition,lat,lng)
                          VALUES (?,?,?,?,?,?,?)""",
                       (b['hospital'], b.get('patient_name','Unknown'), b['blood_type'],
                        units, b.get('condition',''), lat, lng))
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
        condition_lower = b.get('condition', '').lower()
        critical_keywords = ['accident','trauma','critical','hemorrhage','bleeding',
                             'emergency','unconscious','c-section','cardiac','stab',
                             'crush','severe','surgery','rupture','complication']
        if any(kw in condition_lower for kw in critical_keywords) or int(b.get('units_needed', 1)) >= 4:
            urgency = "critical"
            ai_rec = f"CRITICAL: Immediately allocate {b['units_needed']} units of {b['blood_type']}. Activate compatible donors now."
        else:
            urgency = "urgent"
            ai_rec = f"Allocate {b['units_needed']} units of {b['blood_type']} from inventory. Monitor stock levels."

    conn.execute("UPDATE requests SET urgency=?, ai_recommendation=? WHERE id=?", (urgency, ai_rec, req_id))

    if stock >= units:
        conn.execute("UPDATE inventory SET units_available=units_available-? WHERE blood_type=?",
                     (units, b['blood_type']))
        conn.execute("UPDATE requests SET status='allocated', allocated_units=? WHERE id=?",
                     (units, req_id))
        conn.execute("INSERT INTO alerts (type,message,severity) VALUES (?,?,?)",
                     ("emergency", f"🚨 {urgency.upper()}: {b['hospital']} needs {b['units_needed']} units of {b['blood_type']}", "critical" if urgency=="critical" else "warning"))
        conn.execute("INSERT INTO alerts (type,message,severity) VALUES (?,?,?)",
                     ("fulfilled", f"✅ Allocated {b['units_needed']} units of {b['blood_type']} to {b['hospital']}", "success"))
    else:
        conn.execute("INSERT INTO alerts (type,message,severity) VALUES (?,?,?)",
                     ("emergency", f"🚨 {urgency.upper()}: {b['hospital']} needs {b['units_needed']} units of {b['blood_type']} — LOW STOCK", "critical"))

    conn.commit()
    conn.close()

    matched_donors = []
    conn3 = get_db()
    compatible_types = COMPATIBLE_DONORS.get(b['blood_type'], [b['blood_type']])
    placeholders = ",".join("?" * len(compatible_types))
    donor_rows = conn3.execute(
        f"SELECT id, name, blood_type, phone, location FROM donors WHERE eligible=1 AND blood_type IN ({placeholders}) ORDER BY RANDOM() LIMIT 5",
        compatible_types
    ).fetchall()
    matched_donors = [dict(d) for d in donor_rows]
    if matched_donors:
        names = ", ".join([d["name"] for d in matched_donors])
        conn3.execute("INSERT INTO alerts (type,message,severity) VALUES (?,?,?)",
            ("automation", f"🤖 AUTO-ALERT: {len(matched_donors)} donors notified for {b['blood_type']} at {b['hospital']} — {names}", "critical"))
        conn3.commit()
    conn3.close()

    return jsonify({"ok": True, "urgency": urgency, "ai_recommendation": ai_rec,
                    "request_id": req_id, "matched_donors": matched_donors})

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
        {"name": "Amrita Institute of Medical Sciences", "lat": 9.9396,  "lng": 76.3085, "type": "hospital"},
        {"name": "Aster Medcity",                        "lat": 9.9553,  "lng": 76.3127, "type": "hospital"},
        {"name": "Lakeshore Hospital",                   "lat": 9.9708,  "lng": 76.2952, "type": "hospital"},
        {"name": "Medical Trust Hospital",               "lat": 9.9658,  "lng": 76.2897, "type": "hospital"},
        {"name": "Ernakulam General Hospital",           "lat": 9.9843,  "lng": 76.2767, "type": "hospital"},
        {"name": "KIMS Hospital Kalamassery",            "lat": 10.0524, "lng": 76.3141, "type": "hospital"},
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
Give clear, complete, actionable advice. Use bullet points where helpful. Never cut off mid-sentence."""

    reply = gemini(system, msg, history=history, max_tokens=800)
    return jsonify({"reply": reply or "⚠️ AI temporarily unavailable."})

if __name__ == '__main__':   # ✅ CORRECT
    init_db()
    print("\n🩸 LifeLink AI — Blood Emergency Response System")
    print(f"{'✅ Gemini AI active!' if GEMINI_API_KEY else '⚠️  No GEMINI_API_KEY — using fallback logic'}")
    print("📌 Open http://localhost:5000\n")


app.run(
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 5000))
)
