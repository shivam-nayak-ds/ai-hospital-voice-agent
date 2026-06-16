// ═══════════════════════════════════════════════════════════
// Lifeline Hospital Admin Panel — Frontend Logic
// ═══════════════════════════════════════════════════════════

// ─── Elements ────────────────────────────────────────────────
const chatContainer = document.getElementById('chat-container');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const micBtn = document.getElementById('mic-btn');
const visualizer = document.getElementById('visualizer');
const ttsAudio = document.getElementById('tts-audio');
const voiceOverlay = document.getElementById('voice-overlay');
const voiceStatus = document.getElementById('voice-status');
const voiceTranscript = document.getElementById('voice-transcript');
const startVoiceBtn = document.getElementById('start-voice-btn');

// ─── Session ─────────────────────────────────────────────────
let sessionId = localStorage.getItem('asha_session_id');
if (!sessionId) {
    sessionId = "web_user_" + Math.random().toString(36).substring(7);
    localStorage.setItem('asha_session_id', sessionId);
}

// ─── Speech Recognition ──────────────────────────────────────
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition;
let isListening = false;
let isVoiceMode = false;

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'en-IN';

    recognition.onstart = () => {
        isListening = true;
        micBtn.classList.add('active');
        voiceStatus.innerText = "Listening...";
        voiceOverlay.classList.add('listening');
        voiceOverlay.classList.remove('speaking');
    };

    recognition.onend = () => {
        isListening = false;
        micBtn.classList.remove('active');
        voiceOverlay.classList.remove('listening');
        if (isVoiceMode && !ttsAudio.paused) {
            voiceStatus.innerText = "Ananya is speaking...";
        } else if (isVoiceMode) {
            voiceStatus.innerText = "Waiting for you...";
        }
    };

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        voiceTranscript.innerText = transcript;
        if (event.results[0].isFinal) {
            handleSendMessage(transcript);
        }
    };
}


// ═══════════════════════════════════════════════════════════
// TAB SWITCHING
// ═══════════════════════════════════════════════════════════

const tabLoaders = {
    dashboard: fetchDashboard,
    appointments: fetchAppointments,
    doctors: fetchDoctors,
    patients: fetchPatients,
    wards: fetchWards,
    billing: fetchBilling,
};

function switchTab(tabId) {
    // Hide all sections
    document.querySelectorAll('.chat-section, .content-section').forEach(s => {
        s.style.display = 'none';
        s.classList.remove('active');
    });

    // Show selected
    const target = document.getElementById(`${tabId}-tab`);
    if (target) {
        target.style.display = tabId === 'assistant' ? 'flex' : 'block';
        target.classList.add('active');
    }

    // Update sidebar
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.tab === tabId);
    });

    // Load data
    if (tabLoaders[tabId]) tabLoaders[tabId]();
}

document.querySelectorAll('.nav-item').forEach(item => {
    item.onclick = () => switchTab(item.dataset.tab);
});


// ═══════════════════════════════════════════════════════════
// DASHBOARD
// ═══════════════════════════════════════════════════════════

async function fetchDashboard() {
    try {
        const res = await fetch('/api/panel/dashboard');
        const data = await res.json();
        const s = data.stats;

        document.getElementById('stat-appts').textContent = s.today_appointments;
        document.getElementById('stat-doctors').textContent = s.active_doctors;
        document.getElementById('stat-patients').textContent = s.total_patients;
        document.getElementById('stat-beds').textContent = s.occupancy_pct + '%';
        document.getElementById('stat-revenue').textContent = '₹' + (s.today_revenue || 0).toLocaleString();

        // Intents
        const intentsDiv = document.getElementById('intents-list');
        if (data.top_intents && data.top_intents.length > 0) {
            intentsDiv.innerHTML = data.top_intents.map(i =>
                `<div class="feed-item"><span class="label">${i.EVENT_TYPE}</span><span class="badge">${i.cnt}</span></div>`
            ).join('');
        } else {
            intentsDiv.innerHTML = '<p class="muted">No data yet. Chat with the assistant to generate activity.</p>';
        }

        // Activity
        const actDiv = document.getElementById('activity-feed');
        if (data.recent_activity && data.recent_activity.length > 0) {
            actDiv.innerHTML = data.recent_activity.map(a =>
                `<div class="feed-item"><span class="label">${a.ACTION_TYPE}</span><span class="value">${a.ACTION_DETAILS || ''}</span></div>`
            ).join('');
        } else {
            actDiv.innerHTML = '<p class="muted">No recent activity.</p>';
        }
    } catch (e) {
        console.error('Dashboard error:', e);
    }
}


// ═══════════════════════════════════════════════════════════
// CHAT (AI Assistant)
// ═══════════════════════════════════════════════════════════

function appendMessage(role, text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role === 'user' ? 'user-msg' : 'asha-msg'}`;
    const icon = role === 'user' ? 'fa-user' : 'fa-user-nurse';
    msgDiv.innerHTML = `
        <div class="avatar"><i class="fas ${icon}"></i></div>
        <div class="content">${text}</div>
    `;
    chatContainer.appendChild(msgDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

async function handleSendMessage(text) {
    if (!text.trim()) return;
    userInput.value = "";
    appendMessage('user', text);

    try {
        if (isVoiceMode) voiceStatus.innerText = "Ananya is thinking...";

        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: text,
                session_id: sessionId
            })
        });

        const data = await response.json();
        const reply = data.response_text || "I'm sorry, I couldn't process that.";

        appendMessage('asha', reply);

        if (isVoiceMode) playTTS(reply);
    } catch (error) {
        appendMessage('asha', "I'm having trouble connecting right now. Please try again.");
        if (isVoiceMode) setTimeout(() => recognition && recognition.start(), 2000);
    }
}

async function playTTS(text) {
    try {
        visualizer.classList.add('active');
        voiceOverlay.classList.add('speaking');
        voiceOverlay.classList.remove('listening');
        voiceStatus.innerText = "Ananya is speaking...";

        const response = await fetch(`/api/panel/tts?text=${encodeURIComponent(text)}`);
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);

        ttsAudio.src = url;
        ttsAudio.play();

        ttsAudio.onended = () => {
            visualizer.classList.remove('active');
            voiceOverlay.classList.remove('speaking');
            if (isVoiceMode) setTimeout(() => recognition && recognition.start(), 500);
        };
    } catch (error) {
        console.error("TTS Error:", error);
        visualizer.classList.remove('active');
    }
}

// Chat event listeners
sendBtn.onclick = () => handleSendMessage(userInput.value);
userInput.onkeypress = (e) => { if (e.key === 'Enter') handleSendMessage(userInput.value); };

micBtn.onclick = () => {
    if (!recognition) { alert("Speech Recognition not supported. Use Chrome."); return; }
    isListening ? recognition.stop() : recognition.start();
};

// Voice Mode
startVoiceBtn.onclick = () => {
    isVoiceMode = true;
    voiceOverlay.style.display = 'flex';
    startVoiceBtn.style.display = 'none';
    voiceStatus.innerText = "Initializing...";
    const greeting = "Good morning! I am Ananya, your hospital assistant. How can I help you today?";
    appendMessage('asha', greeting);
    playTTS(greeting);
};


// ═══════════════════════════════════════════════════════════
// APPOINTMENTS
// ═══════════════════════════════════════════════════════════

async function fetchAppointments() {
    const tbody = document.querySelector('#appointments-table tbody');
    tbody.innerHTML = '<tr><td colspan="5" class="muted">Loading...</td></tr>';

    try {
        const res = await fetch('/api/panel/appointments');
        const data = await res.json();
        tbody.innerHTML = '';

        if (!data.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="muted">No appointments today.</td></tr>';
            return;
        }

        data.forEach(a => {
            const statusClass = (a.STATUS || 'Confirmed').toLowerCase();
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${a.PATIENT_NAME}</td>
                <td>${a.DOCTOR_NAME}</td>
                <td>${a.APPOINTMENT_TIME}</td>
                <td>${a.APPOINTMENT_DATE}</td>
                <td><span class="status-badge ${statusClass}">${a.STATUS}</span></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="5" class="muted">Error loading appointments.</td></tr>';
    }
}


// ═══════════════════════════════════════════════════════════
// DOCTORS
// ═══════════════════════════════════════════════════════════

async function fetchDoctors() {
    const grid = document.getElementById('doctors-grid');
    grid.innerHTML = '<p class="muted">Loading doctors...</p>';

    try {
        const res = await fetch('/api/panel/doctors');
        const data = await res.json();
        grid.innerHTML = '';

        if (!data.length) {
            grid.innerHTML = '<p class="muted">No doctors found.</p>';
            return;
        }

        data.forEach(d => {
            const statusClass = (d.STATUS || 'Active').toLowerCase().replace(' ', '-');
            const card = document.createElement('div');
            card.className = 'doctor-card';
            card.innerHTML = `
                <i class="fas fa-user-md"></i>
                <h3>${d.NAME}</h3>
                <p>${d.SPECIALIZATION}</p>
                <p>${d.QUALIFICATION || ''}</p>
                <p style="color: ${d.STATUS === 'Active' ? '#10b981' : '#f59e0b'};">${d.STATUS}</p>
                <p style="margin-top:8px; font-size:13px;">${d.EXPERIENCE_YEARS ? d.EXPERIENCE_YEARS + ' yrs exp' : ''} ${d.CONSULTATION_FEE ? '· ₹' + d.CONSULTATION_FEE : ''}</p>
            `;
            grid.appendChild(card);
        });
    } catch (e) {
        grid.innerHTML = '<p class="muted">Error loading doctors.</p>';
    }
}


// ═══════════════════════════════════════════════════════════
// PATIENTS
// ═══════════════════════════════════════════════════════════

async function fetchPatients(searchTerm) {
    const tbody = document.querySelector('#patients-table tbody');
    tbody.innerHTML = '<tr><td colspan="6" class="muted">Loading...</td></tr>';

    try {
        const url = searchTerm
            ? `/api/panel/patients?search=${encodeURIComponent(searchTerm)}`
            : '/api/panel/patients';
        const res = await fetch(url);
        const data = await res.json();
        tbody.innerHTML = '';

        if (!data.length) {
            tbody.innerHTML = '<tr><td colspan="6" class="muted">No patients found.</td></tr>';
            return;
        }

        data.forEach(p => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${p.ID}</td>
                <td>${p.NAME}</td>
                <td>${p.AGE || '-'}</td>
                <td>${p.GENDER || '-'}</td>
                <td>${p.PHONE}</td>
                <td>${p.EMAIL || '-'}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="6" class="muted">Error loading patients.</td></tr>';
    }
}

document.getElementById('patient-search-btn').onclick = () => {
    fetchPatients(document.getElementById('patient-search').value);
};
document.getElementById('patient-search').onkeypress = (e) => {
    if (e.key === 'Enter') fetchPatients(e.target.value);
};


// ═══════════════════════════════════════════════════════════
// WARDS
// ═══════════════════════════════════════════════════════════

async function fetchWards() {
    const grid = document.getElementById('wards-grid');
    grid.innerHTML = '<p class="muted">Loading wards...</p>';

    try {
        const res = await fetch('/api/panel/wards');
        const data = await res.json();
        grid.innerHTML = '';

        if (!data.length) {
            grid.innerHTML = '<p class="muted">No ward data available.</p>';
            return;
        }

        data.forEach(w => {
            const pct = w.OCCUPANCY_PCT || 0;
            const barClass = pct > 80 ? 'high' : pct > 50 ? 'mid' : 'low';
            const card = document.createElement('div');
            card.className = 'ward-card';
            card.innerHTML = `
                <h3><i class="fas fa-bed"></i> ${w.WARD_TYPE}</h3>
                <div class="ward-stat"><span class="label">Total Beds</span><span class="value">${w.TOTAL_BEDS}</span></div>
                <div class="ward-stat"><span class="label">Occupied</span><span class="value">${w.OCCUPIED_BEDS}</span></div>
                <div class="ward-stat"><span class="label">Available</span><span class="value" style="color:#10b981">${w.AVAILABLE_BEDS}</span></div>
                <div class="ward-stat"><span class="label">Rate/Day</span><span class="value">₹${w.PRICE_PER_DAY?.toLocaleString()}</span></div>
                <div class="ward-bar"><div class="ward-bar-fill ${barClass}" style="width:${pct}%"></div></div>
                <p style="font-size:12px;color:var(--text-muted);margin-top:6px;text-align:right">${pct}% occupied</p>
            `;
            grid.appendChild(card);
        });
    } catch (e) {
        grid.innerHTML = '<p class="muted">Error loading ward data.</p>';
    }
}


// ═══════════════════════════════════════════════════════════
// BILLING
// ═══════════════════════════════════════════════════════════

async function fetchBilling() {
    const tbody = document.querySelector('#billing-table tbody');
    tbody.innerHTML = '<tr><td colspan="4" class="muted">Loading...</td></tr>';

    try {
        const [billRes, insRes] = await Promise.all([
            fetch('/api/panel/billing'),
            fetch('/api/panel/insurance')
        ]);
        const billing = await billRes.json();
        const insurance = await insRes.json();

        // Billing table
        tbody.innerHTML = '';
        if (billing.length) {
            billing.forEach(b => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><code style="color:var(--accent-blue)">${b.CODE}</code></td>
                    <td>${b.ITEM_NAME}</td>
                    <td>${b.CATEGORY}</td>
                    <td>₹${b.PRICE?.toLocaleString()}</td>
                `;
                tbody.appendChild(tr);
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="4" class="muted">No billing data.</td></tr>';
        }

        // Insurance list
        const insDiv = document.getElementById('insurance-list');
        if (insurance.length) {
            insDiv.innerHTML = insurance.map(i =>
                `<div class="feed-item">
                    <span class="label">${i.NAME}</span>
                    <span class="status-badge ${i.CASHLESS_AVAILABLE ? 'confirmed' : 'pending'}">
                        ${i.CASHLESS_AVAILABLE ? 'Cashless' : 'Reimbursement'}
                    </span>
                </div>`
            ).join('');
        } else {
            insDiv.innerHTML = '<p class="muted">No insurance data.</p>';
        }
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="4" class="muted">Error loading billing data.</td></tr>';
    }
}


// ═══════════════════════════════════════════════════════════
// INIT — Load dashboard on page load
// ═══════════════════════════════════════════════════════════

window.onload = () => {
    userInput.focus();
    fetchDashboard();
};
