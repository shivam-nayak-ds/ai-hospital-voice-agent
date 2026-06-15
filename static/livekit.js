/**
 * livekit.js
 * ----------
 * Browser client for LiveKit voice assistant.
 * Connects to LiveKit room, publishes mic, subscribes to agent audio.
 */

// ─── State ───────────────────────────────────────────────────────────────────

let room = null;
let isConnected = false;
let currentAssistantMsg = null;

// ─── DOM Elements ────────────────────────────────────────────────────────────

const callBtn = document.getElementById("callBtn");
const callLabel = document.getElementById("callLabel");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const transcriptDiv = document.getElementById("transcript");
const visualizer = document.getElementById("visualizer");

// ─── UI Helpers ──────────────────────────────────────────────────────────────

function setStatus(text, state) {
    statusText.textContent = text;
    statusDot.className = "status-dot " + (state || "");
}

function addMessage(role, text) {
    const msg = document.createElement("div");
    msg.className = `message ${role}`;
    msg.innerHTML = `<div class="role">${role === "user" ? "You" : "Ananya"}</div><div class="text">${text}</div>`;
    transcriptDiv.appendChild(msg);
    transcriptDiv.scrollTop = transcriptDiv.scrollHeight;
    return msg;
}

function updateAssistantMessage(text) {
    if (!currentAssistantMsg) {
        currentAssistantMsg = addMessage("assistant", "");
    }
    currentAssistantMsg.querySelector(".text").textContent += text;
    transcriptDiv.scrollTop = transcriptDiv.scrollHeight;
}

function animateVisualizer(active) {
    if (active) {
        visualizer.classList.remove("inactive");
        const bars = visualizer.querySelectorAll(".bar");
        bars.forEach((bar, i) => {
            const height = 4 + Math.random() * 22;
            bar.style.height = height + "px";
        });
        if (isConnected) setTimeout(() => animateVisualizer(true), 150);
    } else {
        visualizer.classList.add("inactive");
    }
}

// ─── Core: Connect / Disconnect ──────────────────────────────────────────────

async function toggleCall() {
    if (isConnected) {
        await disconnect();
    } else {
        await connect();
    }
}

async function connect() {
    try {
        callBtn.disabled = true;
        setStatus("Connecting...", "");
        callLabel.textContent = "Connecting...";

        // 1. Fetch token from backend
        const tokenRes = await fetch("/api/livekit/token?room=hospital-demo");
        if (!tokenRes.ok) {
            const err = await tokenRes.json();
            throw new Error(err.detail || "Failed to get token");
        }
        const { token, url, room: roomName, user } = await tokenRes.json();

        // 2. Create and connect to LiveKit room
        room = new LivekitClient.Room({
            adaptiveStream: false,
            dynacast: false,
        });

        // Set up event handlers
        room.on(LivekitClient.RoomEvent.TrackSubscribed, onTrackSubscribed);
        room.on(LivekitClient.RoomEvent.TrackUnsubscribed, onTrackUnsubscribed);
        room.on(LivekitClient.RoomEvent.Disconnected, () => {
            setStatus("Disconnected", "");
            isConnected = false;
            updateCallUI(false);
        });
        room.on(LivekitClient.RoomEvent.ActiveSpeakersChanged, onActiveSpeakers);
        room.on(LivekitClient.RoomEvent.DataReceived, onDataReceived);

        // 3. Connect and publish mic
        await room.connect(url, token);
        await room.localParticipant.setMicrophoneEnabled(true);

        isConnected = true;
        setStatus("Connected — Listening", "connected");
        callLabel.textContent = "Tap to end call";
        updateCallUI(true);
        animateVisualizer(true);

        addMessage("assistant", "Connected. How can I help you today?");

    } catch (err) {
        console.error("Connection error:", err);
        setStatus("Error: " + err.message, "");
        callLabel.textContent = "Tap to retry";
    } finally {
        callBtn.disabled = false;
    }
}

async function disconnect() {
    if (room) {
        await room.disconnect();
        room = null;
    }
    isConnected = false;
    setStatus("Disconnected", "");
    updateCallUI(false);
    callLabel.textContent = "Tap to start voice call";
    currentAssistantMsg = null;
}

function updateCallUI(connected) {
    callBtn.classList.toggle("active", connected);
    callBtn.innerHTML = connected ? "&#x260E;" : "&#x1F3A4;";
    if (!connected) {
        visualizer.classList.add("inactive");
    }
}

// ─── LiveKit Event Handlers ──────────────────────────────────────────────────

function onTrackSubscribed(track, publication, participant) {
    // When the agent publishes an audio track, attach it to an <audio> element
    if (track.kind === LivekitClient.Track.Kind.Audio) {
        const el = track.attach();
        el.id = "agent-audio";
        document.body.appendChild(el);
        console.log("Agent audio track subscribed");

        // Reset assistant message for new response
        currentAssistantMsg = null;
    }
}

function onTrackUnsubscribed(track) {
    if (track.kind === LivekitClient.Track.Kind.Audio) {
        const el = document.getElementById("agent-audio");
        if (el) el.remove();
    }
}

function onActiveSpeakers(speakers) {
    // Visual feedback: show who's speaking
    const isUserSpeaking = speakers.some(
        (s) => s.identity === room.localParticipant.identity
    );
    const isAgentSpeaking = speakers.some(
        (s) => s.identity !== room.localParticipant.identity
    );

    if (isUserSpeaking) {
        setStatus("You are speaking...", "connected");
    } else if (isAgentSpeaking) {
        setStatus("Ananya is speaking...", "thinking");
    } else {
        setStatus("Connected — Listening", "connected");
    }
}

/**
 * Handle data messages from the agent (transcripts, responses).
 * The agent worker can publish DataPacket messages to the room.
 */
function onDataReceived(payload, participant) {
    try {
        const data = JSON.parse(new TextDecoder().decode(payload));

        if (data.type === "user_transcript") {
            addMessage("user", data.text);
        } else if (data.type === "agent_response") {
            // Stream token-by-token
            updateAssistantMessage(data.text);
        } else if (data.type === "agent_response_end") {
            currentAssistantMsg = null;
        }
    } catch (e) {
        // Not JSON — ignore
    }
}

// ─── Keyboard Shortcut ──────────────────────────────────────────────────────

document.addEventListener("keydown", (e) => {
    if (e.code === "Space" && !e.target.matches("input, textarea")) {
        e.preventDefault();
        toggleCall();
    }
});
