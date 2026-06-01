// Elements
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

// Session Setup
let sessionId = localStorage.getItem('asha_session_id');
if (!sessionId) {
    sessionId = "web_user_" + Math.random().toString(36).substring(7);
    localStorage.setItem('asha_session_id', sessionId);
}
console.log("Session Active:", sessionId);

// Speech Recognition Setup
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
        voiceStatus.innerText = "Listening...";
        voiceOverlay.classList.add('listening');
        voiceOverlay.classList.remove('speaking');
    };

    recognition.onend = () => {
        isListening = false;
        voiceOverlay.classList.remove('listening');
        if (isVoiceMode && !ttsAudio.paused) {
             voiceStatus.innerText = "Ananya is speaking...";
        } else {
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

// Functions
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

async function playTTS(text) {
    try {
        // Show visualizer while Ananya is speaking
        visualizer.classList.add('active');
        voiceOverlay.classList.add('speaking');
        voiceOverlay.classList.remove('listening');
        voiceStatus.innerText = "Ananya is speaking...";
        
        // Fetch audio from our backend
        const response = await fetch(`/tts?text=${encodeURIComponent(text)}`);
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        
        ttsAudio.src = url;
        ttsAudio.play();
        
        ttsAudio.onended = () => {
            visualizer.classList.remove('active');
            voiceOverlay.classList.remove('speaking');
            
            // 🔥 AUTO-LISTEN: Start listening again after Ananya finishes
            if (isVoiceMode) {
                setTimeout(() => recognition.start(), 500);
            }
        };
    } catch (error) {
        console.error("TTS Error:", error);
        visualizer.classList.remove('active');
    }
}

async function handleSendMessage(text) {
    if (!text.trim()) return;
    
    // Clear input and show user message
    userInput.value = "";
    appendMessage('user', text);
    
    try {
        voiceStatus.innerText = "Ananya is thinking...";
        
        // Send to Backend
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                user_input: text,
                session_id: sessionId
            })
        });
        
        const data = await response.json();
        const ashaReply = data.response;
        
        // Show Asha's message
        appendMessage('asha', ashaReply);
        
        // Speak the reply
        playTTS(ashaReply);
        
    } catch (error) {
        appendMessage('asha', "I apologize, I'm having trouble connecting to my brain right now.");
        if (isVoiceMode) setTimeout(() => recognition.start(), 2000);
    }
}

// Tab Switching Logic
function switchTab(tabId) {
    // Hide all sections
    document.querySelectorAll('.chat-section, .content-section').forEach(s => s.style.display = 'none');
    // Show selected section
    document.getElementById(`${tabId}-tab`).style.display = 'flex';
    
    // Update sidebar active state
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.innerText.toLowerCase().includes(tabId)) item.classList.add('active');
    });

    // Fetch data if needed
    if (tabId === 'appointments') fetchAppointments();
    if (tabId === 'doctors') fetchDoctors();
}

async function fetchAppointments() {
    const tbody = document.querySelector('#appointments-table tbody');
    tbody.innerHTML = '<tr><td colspan="4">Loading...</td></tr>';
    
    try {
        const response = await fetch('/appointments');
        const data = await response.json();
        tbody.innerHTML = '';
        data.forEach(appt => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${appt.PATIENT_NAME}</td>
                <td>${appt.DOCTOR_NAME}</td>
                <td>${appt.APPOINTMENT_TIME}</td>
                <td>${new Date(appt.APPOINTMENT_DATE).toLocaleDateString()}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="4">Error loading data.</td></tr>';
    }
}

async function fetchDoctors() {
    const grid = document.getElementById('doctors-grid');
    grid.innerHTML = 'Loading specialists...';
    
    try {
        const response = await fetch('/doctors');
        const data = await response.json();
        grid.innerHTML = '';
        data.forEach(doc => {
            const card = document.createElement('div');
            card.className = 'doctor-card';
            card.innerHTML = `
                <i class="fas fa-user-md"></i>
                <h3>${doc.NAME}</h3>
                <p>${doc.SPECIALIZATION}</p>
                <p style="color: #10b981;">${doc.STATUS}</p>
            `;
            grid.appendChild(card);
        });
    } catch (e) {
        grid.innerHTML = 'Error loading doctors.';
    }
}

// Attach listeners to nav items
document.querySelectorAll('.nav-item').forEach(item => {
    item.onclick = () => {
        const text = item.innerText.toLowerCase();
        if (text.includes('assistant')) switchTab('assistant');
        if (text.includes('appointments')) switchTab('appointments');
        if (text.includes('reports') || text.includes('specialists')) switchTab('doctors');
    };
});

// Start Voice Mode
startVoiceBtn.onclick = () => {
    isVoiceMode = true;
    startVoiceBtn.style.display = 'none';
    voiceStatus.innerText = "Initializing...";
    
    // Initial Greeting
    const greeting = "Good morning! I am Ananya, your Senior Health Executive. How can I assist you today?";
    appendMessage('asha', greeting);
    playTTS(greeting);
};

// Event Listeners
sendBtn.onclick = () => handleSendMessage(userInput.value);

userInput.onkeypress = (e) => {
    if (e.key === 'Enter') handleSendMessage(userInput.value);
};

micBtn.onclick = () => {
    if (!recognition) {
        alert("Speech Recognition is not supported in your browser. Please use Chrome.");
        return;
    }
    
    if (isListening) {
        recognition.stop();
    } else {
        recognition.start();
    }
};

// Auto-focus input
window.onload = () => userInput.focus();
