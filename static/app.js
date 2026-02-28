// ── LifeLink AI Frontend ──────────────────────────────────────────────
const API = 'http://localhost:5000';
let chatHistory = [];
let mapInstance  = null;
let gaugeCanvases = {};

// ── Init ──────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  console.log("🚀 LifeLink AI Frontend v1.1.0 initialized successfully");

  setupTabs();
  loadDashboard();
  loadTicker();
  setInterval(loadTicker, 30000);
});

// ── Tabs ──────────────────────────────────────────────────────────────
function setupTabs() {
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      tab.classList.add('active');
      const id = 'tab-' + tab.dataset.tab;
      document.getElementById(id).classList.add('active');
      // Lazy load per tab
      if (tab.dataset.tab === 'emergency') loadAllRequests();
      if (tab.dataset.tab === 'donors')    { loadDonors(); loadDonorSummary(); }
      if (tab.dataset.tab === 'inventory') loadInventoryTab();
      if (tab.dataset.tab === 'map')       loadMap();
    });
  });
}

// ── Ticker ────────────────────────────────────────────────────────────
async function loadTicker() {
  try {
    const res    = await fetch(`${API}/api/alerts`);
    const alerts = await res.json();
    const text   = alerts.map(a => `${a.message}`).join('   ·   ');
    document.getElementById('ticker').textContent = text || 'No active alerts';
  } catch { /* silent */ }
}

// ── Dashboard ─────────────────────────────────────────────────────────
async function loadDashboard() {
  try {
    const [stats, inv, reqs] = await Promise.all([
      fetch(`${API}/api/stats`).then(r => r.json()),
      fetch(`${API}/api/inventory`).then(r => r.json()),
      fetch(`${API}/api/requests`).then(r => r.json()),
    ]);

    document.getElementById('d-critical').textContent = stats.critical_count;
    document.getElementById('d-donors').textContent   = stats.total_donors;
    document.getElementById('d-eligible').textContent = `${stats.eligible_donors} eligible now`;
    document.getElementById('d-units').textContent    = stats.total_units;
    document.getElementById('d-lives').textContent    = stats.lives_saved;

    renderGauges('gauge-grid', inv);
    renderRecentRequests(reqs.slice(0, 5));
  } catch (e) { console.error('Dashboard error:', e); }
}

// ── Blood Gauges ──────────────────────────────────────────────────────
function renderGauges(containerId, inventory) {
  const container = document.getElementById(containerId);
  container.innerHTML = '';
  inventory.forEach(item => {
    const pct    = Math.min(100, (item.units_available / 40) * 100);
    const status = item.units_available < 5 ? 'critical' : item.units_available < 12 ? 'low' : 'ok';
    const color  = status === 'critical' ? '#ff2d55' : status === 'low' ? '#ffa000' : '#00e676';

    const card = document.createElement('div');
    card.className = 'gauge-card';
    card.innerHTML = `
      <div class="gauge-blood-type">${item.blood_type}</div>
      <div class="gauge-ring-wrap">
        <canvas width="72" height="72" id="gauge-${item.blood_type.replace('+','p').replace('-','m')}"></canvas>
        <div class="gauge-center">
          <div class="gauge-units" style="color:${color}">${item.units_available}</div>
          <div class="gauge-label-text">units</div>
        </div>
      </div>
      <div class="gauge-status ${status}">${status.toUpperCase()}</div>`;
    container.appendChild(card);

    // Draw ring after DOM insert
    requestAnimationFrame(() => {
      const canvasId = `gauge-${item.blood_type.replace('+','p').replace('-','m')}`;
      drawGaugeRing(canvasId, pct, color);
    });
  });
}

function drawGaugeRing(canvasId, pct, color) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const cx = 36, cy = 36, r = 28;
  const start = -Math.PI / 2;
  const end   = start + (pct / 100) * 2 * Math.PI;

  ctx.clearRect(0, 0, 72, 72);
  // Track
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, 2 * Math.PI);
  ctx.strokeStyle = '#1c2030';
  ctx.lineWidth = 8;
  ctx.stroke();
  // Fill
  ctx.beginPath();
  ctx.arc(cx, cy, r, start, end);
  ctx.strokeStyle = color;
  ctx.lineWidth = 8;
  ctx.lineCap = 'round';
  ctx.stroke();
}

// ── Recent Requests ───────────────────────────────────────────────────
function renderRecentRequests(requests) {
  const el = document.getElementById('recent-requests');
  if (!requests.length) { el.innerHTML = '<p style="color:var(--muted);font-size:13px;padding:10px">No requests yet.</p>'; return; }
  el.innerHTML = `
    <table class="data-table">
      <thead><tr>
        <th>Hospital</th><th>Patient</th><th>Blood Type</th>
        <th>Units</th><th>Urgency</th><th>Status</th><th>Time</th>
      </tr></thead>
      <tbody>${requests.map(r => `
        <tr>
          <td>${r.hospital}</td>
          <td>${r.patient_name || '—'}</td>
          <td><span style="font-family:var(--mono);color:var(--red);font-weight:700">${r.blood_type}</span></td>
          <td>${r.units_needed}</td>
          <td><span class="badge ${r.urgency}">${r.urgency.toUpperCase()}</span></td>
          <td><span class="badge ${r.status}">${r.status}</span></td>
          <td style="color:var(--muted);font-size:11px">${formatTime(r.created_at)}</td>
        </tr>`).join('')}
      </tbody>
    </table>`;
}

// ── Emergency ─────────────────────────────────────────────────────────
async function submitEmergency() {
  const hospital  = document.getElementById('em-hospital').value.trim();
  const patient   = document.getElementById('em-patient').value.trim();
  const bloodType = document.getElementById('em-blood').value;
  const units     = document.getElementById('em-units').value;
  const condition = document.getElementById('em-condition').value.trim();

  if (!hospital || !bloodType || !units) {
    alert('Please fill in Hospital, Blood Type and Units.'); return;
  }

  const btn = document.querySelector('#tab-emergency .btn-danger');
  btn.disabled = true; btn.textContent = '🤖 AI Analyzing...';

  const result = document.getElementById('em-result');
  result.innerHTML = `<div class="ai-placeholder"><div style="font-size:36px">🤖</div><div>AI is classifying this emergency...</div></div>`;

  try {
    const res  = await fetch(`${API}/api/requests/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ hospital, patient_name: patient, blood_type: bloodType, units_needed: parseInt(units), condition })
    });
    const data = await res.json();

    const urgencyColors = { critical: '#ff2d55', urgent: '#ffa000', routine: '#00e676' };
    const color = urgencyColors[data.urgency] || '#fff';

    result.innerHTML = `
      <div class="ai-result">
        <div class="urgency-banner ${data.urgency}">
          <div class="urgency-title" style="color:${color}">
            ${data.urgency === 'critical' ? '🚨' : data.urgency === 'urgent' ? '⚠️' : '✅'}
            ${data.urgency.toUpperCase()} — Request #${data.request_id}
          </div>
          <div style="font-size:12px;color:var(--muted)">AI Classification Complete</div>
        </div>
        <div style="font-size:12px;color:var(--muted);margin-bottom:6px;font-weight:700;text-transform:uppercase;letter-spacing:.8px">AI Recommendation</div>
        <div class="ai-rec-box">${data.ai_recommendation}</div>
        <div style="margin-top:12px;display:flex;gap:10px;font-size:12px">
          <span style="color:var(--accent)">✅ Request logged to database</span>
          <span style="color:var(--muted)">·</span>
          <span style="color:var(--muted)">Inventory auto-updated</span>
        </div>
      </div>`;

    // 🤖 Trigger automation if critical
    if (data.urgency === 'critical' && data.matched_donors && data.matched_donors.length > 0) {
      setTimeout(() => runDonorAutomation(data.matched_donors, bloodType, hospital), 600);
    }

    // Clear form
    ['em-hospital','em-patient','em-units','em-condition'].forEach(id => document.getElementById(id).value = '');
    document.getElementById('em-blood').value = '';
    loadTicker();
  } catch (e) {
    result.innerHTML = `<div style="color:var(--red);font-size:13px;padding:20px">⚠️ Error submitting request. Is the server running?</div>`;
  }
  btn.disabled = false; btn.textContent = '🚨 Submit Emergency Request';
}

// ── AI Donor Automation ───────────────────────────────────────────────
function runDonorAutomation(donors, bloodType, hospital) {
  const panel = document.getElementById('automation-panel');
  const log   = document.getElementById('automation-log');
  const badge = document.getElementById('auto-badge');

  panel.style.display = 'block';
  panel.classList.add('automation-appear');
  log.innerHTML = '';
  badge.textContent = 'RUNNING';
  badge.className = 'auto-badge running';

  // Header status
  document.getElementById('auto-status').innerHTML =
    `🤖 AI identified <strong>${donors.length} compatible donor${donors.length > 1 ? 's' : ''}</strong> for <strong>${bloodType}</strong> — auto-alerting now...`;

  const smsMessages = [
    `[LifeLink AI] 🚨 URGENT: ${bloodType} blood needed at ${hospital}. You are compatible. Please respond immediately: http://lifelink.local/respond`,
    `[LifeLink AI] 🩸 Critical blood request at ${hospital} needs ${bloodType}. As an eligible donor you can help save a life. Reply YES to confirm.`,
    `[LifeLink AI] ALERT: Emergency at ${hospital}. ${bloodType} blood required urgently. Your donation can make the difference. Call: 0484-000-BLOOD`,
  ];

  let completed = 0;

  donors.forEach((donor, i) => {
    // Step 1: show "Contacting..." row
    setTimeout(() => {
      const row = document.createElement('div');
      row.className = 'auto-row';
      row.id = `auto-row-${i}`;
      const msg = smsMessages[i % smsMessages.length];
      row.innerHTML = `
        <div class="auto-row-top">
          <div class="auto-donor-info">
            <span class="auto-blood-badge">${donor.blood_type}</span>
            <span class="auto-donor-name">${donor.name}</span>
            <span class="auto-donor-loc">📍 ${donor.location}</span>
          </div>
          <div class="auto-status-pill sending">
            <span class="pulse-dot"></span> Sending SMS...
          </div>
        </div>
        <div class="auto-sms-preview">${msg}</div>`;
      log.appendChild(row);
      log.scrollTop = log.scrollHeight;
    }, i * 900);

    // Step 2: mark as sent
    setTimeout(() => {
      const row = document.getElementById(`auto-row-${i}`);
      if (row) {
        row.querySelector('.auto-status-pill').className = 'auto-status-pill sent';
        row.querySelector('.auto-status-pill').innerHTML = '✅ SMS Delivered';
      }
      completed++;
      if (completed === donors.length) {
        // All done
        setTimeout(() => {
          badge.textContent = 'COMPLETE';
          badge.className = 'auto-badge complete';
          document.getElementById('auto-status').innerHTML =
            `✅ Automation complete — <strong>${donors.length} donor${donors.length > 1 ? 's' : ''}</strong> alerted in <strong>${(donors.length * 0.9).toFixed(1)}s</strong>. Awaiting responses.`;
          document.getElementById('auto-summary').style.display = 'flex';
          document.getElementById('auto-summary-count').textContent = donors.length;
        }, 400);
      }
    }, i * 900 + 1400);
  });
}

async function loadAllRequests() {
  const res  = await fetch(`${API}/api/requests`);
  const data = await res.json();
  const el   = document.getElementById('all-requests');
  el.innerHTML = `
    <table class="data-table">
      <thead><tr><th>Hospital</th><th>Patient</th><th>Blood</th><th>Units</th><th>Urgency</th><th>Status</th><th>AI Note</th><th>Time</th></tr></thead>
      <tbody>${data.map(r => `
        <tr>
          <td>${r.hospital}</td>
          <td>${r.patient_name || '—'}</td>
          <td><span style="font-family:var(--mono);color:var(--red);font-weight:700">${r.blood_type}</span></td>
          <td>${r.units_needed}</td>
          <td><span class="badge ${r.urgency}">${r.urgency?.toUpperCase()}</span></td>
          <td><span class="badge ${r.status}">${r.status}</span></td>
          <td style="color:var(--muted);font-size:11px;max-width:200px">${r.ai_recommendation || '—'}</td>
          <td style="color:var(--muted);font-size:11px">${formatTime(r.created_at)}</td>
        </tr>`).join('')}
      </tbody>
    </table>`;
}

// ── Donors ────────────────────────────────────────────────────────────
async function registerDonor() {
  const name     = document.getElementById('dn-name').value.trim();
  const age      = document.getElementById('dn-age').value;
  const blood    = document.getElementById('dn-blood').value;
  const phone    = document.getElementById('dn-phone').value.trim();
  const location = document.getElementById('dn-location').value.trim();
  const lastdon  = document.getElementById('dn-lastdon').value;

  if (!name || !blood) { alert('Name and Blood Type are required.'); return; }

  const btn = document.querySelector('#tab-donors .btn-primary');
  btn.disabled = true; btn.textContent = 'Registering...';

  const res  = await fetch(`${API}/api/donors/register`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, age: parseInt(age)||25, blood_type: blood, phone, location, last_donated: lastdon })
  });
  const data = await res.json();

  const resultEl = document.getElementById('dn-result');
  resultEl.innerHTML = data.eligible
    ? `<div style="color:var(--accent);font-size:13px;padding:10px;background:var(--accent-d);border-radius:8px;border:1px solid rgba(0,230,118,.2)">✅ ${name} registered successfully! <strong>Eligible to donate.</strong></div>`
    : `<div style="color:#ffa000;font-size:13px;padding:10px;background:rgba(255,160,0,.1);border-radius:8px">⚠️ ${name} registered. <strong>Not yet eligible</strong> (must wait 90 days since last donation).</div>`;

  ['dn-name','dn-age','dn-phone','dn-location'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('dn-blood').value = '';
  loadDonors(); loadDonorSummary(); loadTicker();
  btn.disabled = false; btn.textContent = '✅ Register Donor';
  setTimeout(() => resultEl.innerHTML = '', 5000);
}

async function loadDonors() {
  const res  = await fetch(`${API}/api/donors`);
  const data = await res.json();
  document.getElementById('donors-table').innerHTML = `
    <table class="data-table">
      <thead><tr><th>Name</th><th>Blood Type</th><th>Age</th><th>Phone</th><th>Location</th><th>Last Donated</th><th>Donations</th><th>Status</th></tr></thead>
      <tbody>${data.map(d => `
        <tr>
          <td style="font-weight:600">${d.name}</td>
          <td><span style="font-family:var(--mono);color:var(--red);font-weight:700">${d.blood_type}</span></td>
          <td>${d.age || '—'}</td>
          <td style="color:var(--muted);font-size:11px">${d.phone || '—'}</td>
          <td>${d.location || '—'}</td>
          <td style="color:var(--muted);font-size:11px">${d.last_donated || 'Never'}</td>
          <td style="font-family:var(--mono);text-align:center">${d.total_donations}</td>
          <td><span class="badge ${d.eligible ? 'routine' : 'fulfilled'}">${d.eligible ? 'ELIGIBLE' : 'INELIGIBLE'}</span></td>
        </tr>`).join('')}
      </tbody>
    </table>`;
}

async function loadDonorSummary() {
  const res  = await fetch(`${API}/api/donors`);
  const data = await res.json();
  const el   = document.getElementById('donor-summary');

  const byBlood = {};
  data.forEach(d => { byBlood[d.blood_type] = (byBlood[d.blood_type] || 0) + 1; });

  el.innerHTML = `
    <div style="margin-bottom:16px">
      <div style="display:flex;gap:24px;margin-bottom:14px">
        <div><div style="font-family:var(--mono);font-size:24px;color:var(--accent)">${data.filter(d=>d.eligible).length}</div><div style="font-size:11px;color:var(--muted)">Eligible Now</div></div>
        <div><div style="font-family:var(--mono);font-size:24px;color:var(--red)">${data.filter(d=>!d.eligible).length}</div><div style="font-size:11px;color:var(--muted)">Ineligible</div></div>
        <div><div style="font-family:var(--mono);font-size:24px;color:var(--blue)">${data.length}</div><div style="font-size:11px;color:var(--muted)">Total</div></div>
      </div>
    </div>
    <div class="donor-cards">
      ${data.slice(0,6).map(d => `
        <div class="donor-mini">
          <div class="donor-avatar">${d.blood_type}</div>
          <div class="donor-info">
            <div class="donor-name">${d.name}</div>
            <div class="donor-meta">${d.location} · ${d.total_donations} donations</div>
          </div>
          <div class="eligible-dot ${d.eligible ? 'yes' : 'no'}" title="${d.eligible ? 'Eligible' : 'Not eligible'}"></div>
        </div>`).join('')}
    </div>`;
}

// ── Inventory Tab ─────────────────────────────────────────────────────
async function loadInventoryTab() {
  const res = await fetch(`${API}/api/inventory`);
  const inv = await res.json();

  renderGauges('inv-gauge-grid', inv);

  const grid = document.getElementById('inv-update-grid');
  grid.innerHTML = inv.map(item => `
    <div class="inv-update-card">
      <div class="inv-bt-label">${item.blood_type}</div>
      <input class="inv-inp" id="inv-${item.blood_type.replace('+','p').replace('-','m')}" type="number" value="${item.units_available}" min="0" max="999"/>
      <br/>
      <button class="inv-save-btn" onclick="saveInventory('${item.blood_type}')">Save</button>
    </div>`).join('');
}

async function saveInventory(bloodType) {
  const id    = `inv-${bloodType.replace('+','p').replace('-','m')}`;
  const units = parseInt(document.getElementById(id).value);
  await fetch(`${API}/api/inventory/update`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ blood_type: bloodType, units })
  });
  loadInventoryTab();
}

// ── Map ───────────────────────────────────────────────────────────────
async function loadMap() {
  if (!mapInstance) {
    mapInstance = L.map('map', { zoomControl: true }).setView([12.9716, 77.5946], 12);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '© OpenStreetMap © CARTO', maxZoom: 19
    }).addTo(mapInstance);
  } else {
    mapInstance.eachLayer(l => { if (l instanceof L.Marker) mapInstance.removeLayer(l); });
  }

  const res  = await fetch(`${API}/api/map`);
  const data = await res.json();

  // Hospital markers
  data.hospitals.forEach(h => {
    const icon = L.divIcon({
      html: `<div style="background:#2979ff;width:14px;height:14px;border-radius:50%;border:2px solid #fff;box-shadow:0 0 8px #2979ff"></div>`,
      className: '', iconSize: [14, 14]
    });
    L.marker([h.lat, h.lng], { icon })
      .addTo(mapInstance)
      .bindPopup(`<b style="color:#2979ff">🏥 ${h.name}</b>`);
  });

  // Donor markers
  data.donors.forEach(d => {
    const color = d.eligible ? '#00e676' : '#4a5568';
    const icon  = L.divIcon({
      html: `<div style="background:${color};width:12px;height:12px;border-radius:50%;border:2px solid #fff;box-shadow:0 0 6px ${color}"></div>`,
      className: '', iconSize: [12, 12]
    });
    L.marker([d.lat, d.lng], { icon })
      .addTo(mapInstance)
      .bindPopup(`<b style="color:${color}">👤 ${d.name}</b><br/>Blood: <b>${d.blood_type}</b><br/>${d.eligible ? '✅ Eligible' : '❌ Not eligible'}`);
  });

  // Emergency request markers
  data.requests.forEach(r => {
    const icon = L.divIcon({
      html: `<div style="background:#ff2d55;width:16px;height:16px;border-radius:50%;border:2px solid #fff;box-shadow:0 0 10px #ff2d55;animation:pulse 1s infinite"></div>`,
      className: '', iconSize: [16, 16]
    });
    L.marker([r.lat, r.lng], { icon })
      .addTo(mapInstance)
      .bindPopup(`<b style="color:#ff2d55">🚨 ${r.hospital}</b><br/>Needs: <b>${r.units_needed} units ${r.blood_type}</b><br/>Priority: <b>${r.urgency?.toUpperCase()}</b>`);
  });
}

// ── AI Chat ───────────────────────────────────────────────────────────
function quickChat(msg) {
  document.getElementById('chat-inp').value = msg;
  sendChat();
}

async function sendChat() {
  const inp = document.getElementById('chat-inp');
  const msg = inp.value.trim();
  if (!msg) return;
  inp.value = '';

  appendBubble(msg, 'user');
  chatHistory.push({ role: 'user', content: msg });

  const typing = appendBubble('LifeLink AI is thinking...', 'ai typing');

  try {
    const res  = await fetch(`${API}/api/ai/chat`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg, history: chatHistory.slice(-8) })
    });
    const data = await res.json();
    typing.remove();
    const reply = data.reply || 'Sorry, I could not process that.';
    appendBubble(reply, 'ai');
    chatHistory.push({ role: 'model', content: reply });
  } catch {
    typing.remove();
    appendBubble('⚠️ Connection error. Is the server running?', 'ai');
  }
}

function appendBubble(text, cls) {
  const msgs = document.getElementById('chat-messages');
  const div  = document.createElement('div');
  div.className = `chat-bubble ${cls}`;
  div.textContent = text;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
  return div;
}

// ── AI Predictions ────────────────────────────────────────────────────
async function loadPredictions() {
  const grid = document.getElementById('predictions-grid');
  grid.innerHTML = `<div class="ai-placeholder"><div style="font-size:40px">🔮</div><div>AI is analyzing blood stock trends...</div></div>`;

  const res  = await fetch(`${API}/api/ai/predict`, { method: 'POST' });
  const data = await res.json();

  grid.innerHTML = data.predictions.map((p, i) => `
    <div class="pred-card ${p.risk}" style="animation-delay:${i * 0.06}s">
      <div class="pred-bt">${p.blood_type}</div>
      <div class="pred-risk ${p.risk}">${p.risk.toUpperCase()} RISK</div>
      <div class="pred-days">⏱ ~${p.days_until_shortage} days until critical</div>
      <div class="pred-rec">${p.recommendation}</div>
    </div>`).join('');
}

// ── Helpers ───────────────────────────────────────────────────────────
function formatTime(ts) {
  if (!ts) return '—';
  try {
    const d = new Date(ts);
    return d.toLocaleDateString('en-IN', { day:'numeric', month:'short' }) + ' ' +
           d.toLocaleTimeString('en-IN', { hour:'2-digit', minute:'2-digit' });
  } catch { return ts; }
}
