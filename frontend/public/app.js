/**
 * Configuration & Constants
 */
const API_BASE = window.location.origin; 
const WS_BASE = API_BASE.replace(/^http/, "ws");

// State Variables
let USER_ID = null;
let SESSION_ID = null;
let isSidebarOpen = true; 

// Voice State
let isRecording = false;
let isConnecting = false;
let socket = null;
let audioContext = null;
let sourceNode = null;
let processorNode = null;
let nextStartTime = 0;       
let audioQueue = []; 

// DOM Elements
const loginSection = document.getElementById('login-section');
const chatSection = document.getElementById('chat-section');
const loginForm = document.getElementById('login-form');
const loginError = document.getElementById('login-error');
const chatContainer = document.getElementById('chat-container');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const micBtn = document.getElementById('mic-btn');
const voiceStatus = document.getElementById('voice-status');
const uploadBtn = document.getElementById('upload-btn');
const fileInput = document.getElementById('file-input');
const sessionBadge = document.getElementById('session-badge');
const logoutBtn = document.getElementById('logout-btn');
const statusDiv = document.getElementById('status');
const newChatBtn = document.getElementById('new-chat-btn');
const historyList = document.getElementById('history-list');
const sidebar = document.getElementById('sidebar');
const toggleSidebarBtn = document.getElementById('toggle-sidebar-btn');
const closeSidebarBtn = document.getElementById('close-sidebar-btn');
const userAvatar = document.getElementById('user-avatar');
const usernameDisplay = document.getElementById('username-display');

/**
 * 1. Initialization & Persistence
 */
document.addEventListener('DOMContentLoaded', () => {
    // Check Local Storage
    const storedUser = localStorage.getItem('chat_user_id');
    const storedSession = localStorage.getItem('chat_session_id');

    if (storedUser && storedSession) {
        USER_ID = storedUser;
        SESSION_ID = storedSession;
        console.log("Restoring session:", SESSION_ID);
        initializeChat(false); 
    }
});

/**
 * 2. Sidebar & Layout Logic
 */
function toggleSidebar() {
    const isMobile = window.innerWidth < 768;

    if (isMobile) {
        if (sidebar.classList.contains('-translate-x-full')) {
            sidebar.classList.remove('-translate-x-full');
        } else {
            sidebar.classList.add('-translate-x-full');
        }
    } else {
        if (isSidebarOpen) {
            sidebar.style.width = "0px";
            sidebar.style.opacity = "0";
            sidebar.classList.add('overflow-hidden'); 
            isSidebarOpen = false;
        } else {
            sidebar.style.width = "16rem"; 
            sidebar.style.opacity = "1";
            sidebar.classList.remove('overflow-hidden');
            isSidebarOpen = true;
        }
    }
}

toggleSidebarBtn.addEventListener('click', toggleSidebar);
closeSidebarBtn.addEventListener('click', () => sidebar.classList.add('-translate-x-full'));

/**
 * 3. Input Auto-Resize Logic
 */
function adjustTextareaHeight() {
    userInput.style.height = 'auto'; // Reset height
    userInput.style.height = Math.min(userInput.scrollHeight, 192) + 'px'; // Max height ~12rem (48 in tailwind)
}

userInput.addEventListener('input', adjustTextareaHeight);

/**
 * 4. Authentication Logic
 */
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const submitBtn = loginForm.querySelector('button[type="submit"]');

    submitBtn.disabled = true;
    submitBtn.innerText = "Signing in...";
    loginError.classList.add('hidden');

    try {
        const response = await fetch(`${API_BASE}/aulogin`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        if (!response.ok) throw new Error("Auth failed");

        const data = await response.json();
        USER_ID = data.user_id || username;
        SESSION_ID = data.session_id || crypto.randomUUID();

        // Store user data including admin status
        localStorage.setItem('chat_user_id', USER_ID);
        localStorage.setItem('chat_session_id', SESSION_ID);
        localStorage.setItem('user_isadmin', String(data.isadmin));
        localStorage.setItem('user_org', String(data.org));

        initializeChat(true); 

    } catch (err) {
        console.error("Login failed:", err);
        loginError.classList.remove('hidden');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerText = "Sign In";
    }
});

function initializeChat(isNewLogin) {
    loginSection.classList.add('hidden');
    chatSection.classList.remove('hidden');
    chatSection.classList.add('flex');

    updateSessionBadge();

    statusDiv.innerText = "Connected";
    if (usernameDisplay) usernameDisplay.innerText = USER_ID;
    if (userAvatar) userAvatar.innerText = USER_ID.charAt(0).toUpperCase();

    // Show admin menu if user is admin
    const isAdmin = localStorage.getItem('user_isadmin') === 'true';
    if (isAdmin) {
        showAdminMenu();
    }

    loadSessions();

    if (!isNewLogin) {
        loadHistory(SESSION_ID);
    }
}

logoutBtn.addEventListener('click', () => {
    // Clear all stored auth data
    localStorage.removeItem('chat_user_id');
    localStorage.removeItem('chat_session_id');
    localStorage.removeItem('user_isadmin');
    localStorage.removeItem('user_org');
    localStorage.removeItem('admin_org_id');
    localStorage.removeItem('admin_username');
    localStorage.removeItem('admin_authenticated');

    window.location.reload();
});

/**
 * 5. History & Session Management
 */
async function loadSessions() {
    try {
        const res = await fetch(`${API_BASE}/sessions?user_id=${USER_ID}`);
        if(!res.ok) return;
        
        let data = await res.json();
        
        // --- FIX: Handle both Array (new backend) and Object (old backend) formats ---
        let sessions = [];
        if (Array.isArray(data)) {
            sessions = data;
        } else if (data && data.sessions) {
            sessions = data.sessions;
        }
        // -----------------------------------------------------------------------------

        historyList.innerHTML = ''; 
        
        // Use the safe 'sessions' variable instead of 'data'
        sessions.forEach(session => {
            const btn = document.createElement('button');
            const isActive = session.session_id === SESSION_ID;

            btn.className = `w-full text-left px-3 py-3 text-sm rounded-lg mb-1 transition flex items-center gap-2 group ${
                isActive 
                ? "bg-indigo-600 text-white font-medium shadow-md" 
                : "text-slate-400 hover:bg-slate-800 hover:text-white"
            }`;
            
            const iconHTML = isActive 
                ? `<svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"></path></svg>`
                : `<svg class="w-4 h-4 flex-shrink-0 opacity-50 group-hover:opacity-100" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-3.582 8-8 8a8.013 8.013 0 01-5.685-2.356L3 21l1.15-3.15a8 8 0 112.85-2.85L7 15"></path></svg>`;

            btn.innerHTML = `${iconHTML} <span class="truncate">${session.title || "Untitled Session"}</span>`;
            btn.title = session.title; 
            
            btn.onclick = () => {
                switchSession(session.session_id);
            };
            historyList.appendChild(btn);
        });
    } catch (err) {
        console.error("Error loading sessions:", err);
    }
}

async function loadHistory(sessionId) {
    chatContainer.innerHTML = ''; 
    try {
        const res = await fetch(`${API_BASE}/history?session_id=${sessionId}`);
        if(!res.ok) return;
        const data = await res.json();
        
        if (data.history.length === 0) {
            const welcomeDiv = document.createElement('div');
            welcomeDiv.className = "flex gap-4 max-w-3xl";
            welcomeDiv.innerHTML = `
                <div class="w-8 h-8 rounded-full bg-indigo-600 flex-shrink-0 flex items-center justify-center text-white text-xs font-bold">AI</div>
                <div class="bg-white text-slate-700 p-4 rounded-2xl rounded-tl-none border border-slate-200 shadow-sm max-w-[85%]">
                    <p>Welcome back! How can I help you today?</p>
                </div>`;
            chatContainer.appendChild(welcomeDiv);
        } else {
            data.history.forEach(msg => {
                appendMessage(msg.role, msg.content);
            });
        }
    } catch (err) {
        console.error("Error loading history:", err);
    }
}

function switchSession(newSessionId) {
    SESSION_ID = newSessionId;
    localStorage.setItem('chat_session_id', SESSION_ID);
    updateSessionBadge();
    loadSessions(); 
    loadHistory(SESSION_ID);
    
    if (window.innerWidth < 768) {
        sidebar.classList.add('-translate-x-full');
    }
}

newChatBtn.addEventListener('click', () => {
    SESSION_ID = crypto.randomUUID();
    localStorage.setItem('chat_session_id', SESSION_ID);
    chatContainer.innerHTML = ''; 
    appendMessage('assistant', "Starting a new conversation. What's on your mind?");
    updateSessionBadge();
    loadSessions(); 
});

function updateSessionBadge() {
    sessionBadge.innerText = `Session: ${SESSION_ID.slice(0, 8)}`;
}

/**
 * 6. Chat UI Logic - Updated for Markdown
 */
function appendMessage(role, text, artifacts = null) {
    const wrapperDiv = document.createElement('div');
    const isUser = role === 'user';
    
    wrapperDiv.className = `flex gap-4 max-w-3xl ${isUser ? "flex-row-reverse self-end" : "self-start"}`;

    const avatar = document.createElement('div');
    avatar.className = `w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold shadow-sm ${
        isUser ? "bg-indigo-100 text-indigo-600" : "bg-indigo-600 text-white"
    }`;
    avatar.innerText = isUser ? "ME" : "AI";

    const bubble = document.createElement('div');
    bubble.className = isUser 
        ? "bg-indigo-600 text-white p-4 rounded-2xl rounded-tr-none shadow-md" 
        : "bg-white text-slate-700 p-4 rounded-2xl rounded-tl-none border border-slate-200 shadow-sm";
    
    let contentHtml;

    if (isUser) {
        contentHtml = text.replace(/\n/g, '<br>');
    } else {
        // AI: Markdown Rendering
        let cleanText = text;

        // 1. FIXED: Force newline between Header and List if on same line (e.g. "### Header: 1. Item")
        cleanText = cleanText.replace(/(#+ [^\n]+?)(:?)\s+([0-9]+\. )/g, '$1$2\n\n$3');

        // 2. Fix "Lazy" Markdown: Add double newlines before lists and headers
        cleanText = cleanText.replace(/([^\n])\n([*-] |[0-9]+\. )/g, '$1\n\n$2');
        cleanText = cleanText.replace(/([^\n])\n(#+ )/g, '$1\n\n$2');

        // 3. Parse Markdown
        // Check for 'marked.parse' (modern) or 'marked' (legacy)
        if (typeof marked !== 'undefined') {
            try {
                contentHtml = marked.parse(cleanText, { breaks: true });
            } catch (e) {
                console.error("Markdown parsing failed:", e);
                contentHtml = cleanText.replace(/\n/g, '<br>');
            }
        } else {
            console.warn('Marked library not loaded.');
            contentHtml = cleanText.replace(/\n/g, '<br>');
        }
        
        // Wrap in div
        contentHtml = `<div class="markdown-content">${contentHtml}</div>`;
    }
    
    // Prose classes for typography
    bubble.innerHTML = `<div class="prose ${isUser ? 'prose-invert' : 'prose-slate'} max-w-none text-sm leading-relaxed">${contentHtml}</div>`;
    
    if (artifacts && artifacts.search_sources) {
        bubble.innerHTML += `
            <div class="mt-3 pt-3 border-t ${isUser ? 'border-indigo-500' : 'border-slate-100'}">
                <details class="text-xs group">
                    <summary class="font-semibold opacity-75 cursor-pointer flex items-center gap-1 hover:opacity-100 transition">
                        <span>📚 View Sources</span>
                    </summary>
                    <div class="mt-2 p-2 bg-black/5 rounded italic leading-snug">${artifacts.search_sources}</div>
                </details>
            </div>`;
    }
    
    wrapperDiv.appendChild(avatar);
    wrapperDiv.appendChild(bubble);
    
    chatContainer.appendChild(wrapperDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;

    appendMessage('user', message);
    userInput.value = "";
    adjustTextareaHeight();
    
    const loadingId = "loading-" + Date.now();
    const loadingDiv = document.createElement('div');
    loadingDiv.id = loadingId;
    loadingDiv.className = "flex items-center gap-2 ml-12 text-slate-400 text-xs italic mb-4";
    loadingDiv.innerHTML = `<span class="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></span> Assistant is thinking...`;
    
    chatContainer.appendChild(loadingDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;

    try {
        const response = await fetch(`${API_BASE}/rag/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: SESSION_ID,
                user_id: USER_ID,
                message: message
            })
        });

        document.getElementById(loadingId)?.remove();

        if (!response.ok) throw new Error("API Error");

        const data = await response.json();
        appendMessage('assistant', data.reply, data.artifacts);
        loadSessions(); 

    } catch (err) {
        document.getElementById(loadingId)?.remove();
        console.error(err);
        appendMessage('system', "⚠️ Error sending message. Please try again.");
    }
}

/**
 * 7. File Upload Logic
 */
async function handleUpload() {
    const file = fileInput.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    appendMessage('system', `Uploading <strong>${file.name}</strong>...`);

    try {
        const response = await fetch(`${API_BASE}/upload?session_id=${SESSION_ID}`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error("Upload failed");

        appendMessage('system', `✅ File uploaded successfully.`);
    } catch (err) {
        appendMessage('system', "❌ Upload failed.");
    } finally {
        fileInput.value = ''; 
    }
}

/**
 * 8. Real-time Voice Logic
 */
function floatTo16BitPCM(input) {
    const output = new Int16Array(input.length);
    for (let i = 0; i < input.length; i++) {
        const s = Math.max(-1, Math.min(1, input[i]));
        output[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return output;
}

function convertInt16ToFloat32(int16Array) {
    const float32 = new Float32Array(int16Array.length);
    for (let i = 0; i < int16Array.length; i++) {
        float32[i] = int16Array[i] >= 0 ? int16Array[i] / 32767 : int16Array[i] / 32768;
    }
    return float32;
}

async function startVoiceSession() {
    if (isConnecting) return;
    if (isRecording) {
        stopVoiceSession();
        return;
    }

    try {
        isConnecting = true;
        micBtn.disabled = true; 
        
        if (!audioContext || audioContext.state === 'closed') {
            audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
        }
        if (audioContext.state === 'suspended') {
            await audioContext.resume();
        }

        const wsUrl = `${WS_BASE}/ws/realtime?session_id=${SESSION_ID}&user_id=${USER_ID}`;
        console.log("Connecting to WS:", wsUrl);
        socket = new WebSocket(wsUrl);
        
        socket.onopen = async () => {
            console.log("WebSocket Connected");
            isConnecting = false;
            isRecording = true;
            
            micBtn.disabled = false;
            micBtn.classList.remove("text-slate-400");
            micBtn.classList.add("bg-red-500", "text-white", "animate-pulse");
            voiceStatus.classList.remove("hidden");
            
            await startMicrophone(audioContext);
        };

        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.type === "response.audio.delta" && data.delta) {
                playAudioChunk(data.delta);
            }

            if (data.type === "input_audio_buffer.speech_started") {
                console.log("Speech started detected: Stopping audio.");
                stopAudioPlayback();
            }

            if (data.type === "conversation.item.input_audio_transcription.completed") {
                const transcript = data.transcript;
                if (transcript) appendMessage("user", transcript);
            }
            
            if (data.type === "response.audio_transcript.done") {
                const transcript = data.transcript;
                if (transcript) appendMessage("assistant", transcript);
            }
        };

        socket.onerror = (err) => {
            console.error("WebSocket Error:", err);
            stopVoiceSession();
        };

        socket.onclose = () => {
            console.log("WebSocket Closed");
            stopVoiceSession();
        };

    } catch (err) {
        console.error("Voice Initialization Error:", err);
        stopVoiceSession();
    }
}

async function startMicrophone(ctx) {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        if (!ctx || ctx.state === 'closed') return;

        sourceNode = ctx.createMediaStreamSource(stream);
        processorNode = ctx.createScriptProcessor(4096, 1, 1);

        processorNode.onaudioprocess = (e) => {
            if (!isRecording || !socket || socket.readyState !== WebSocket.OPEN) return;
            
            const inputData = e.inputBuffer.getChannelData(0);
            const pcm16 = floatTo16BitPCM(inputData);
            
            const reader = new FileReader();
            reader.onload = () => {
                const base64Audio = reader.result.split(',')[1];
                socket.send(JSON.stringify({
                    type: "input_audio_buffer.append",
                    audio: base64Audio
                }));
            };
            reader.readAsDataURL(new Blob([pcm16.buffer]));
        };

        sourceNode.connect(processorNode);
        processorNode.connect(ctx.destination);
    } catch (err) {
        console.error("Mic Error:", err);
        stopVoiceSession();
    }
}

function stopVoiceSession() {
    isRecording = false;
    isConnecting = false;
    stopAudioPlayback();
    
    micBtn.disabled = false;
    micBtn.classList.remove("bg-red-500", "text-white", "animate-pulse");
    micBtn.classList.add("text-slate-400");
    voiceStatus.classList.add("hidden");

    if (sourceNode) { sourceNode.disconnect(); sourceNode = null; }
    if (processorNode) { processorNode.disconnect(); processorNode = null; }
    if (socket) { socket.close(); socket = null; }
    if (audioContext) { 
        audioContext.close(); 
        audioContext = null; 
    }
}

function playAudioChunk(base64Audio) {
    if (!audioContext) return;
    
    const binary = window.atob(base64Audio);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    const float32Data = convertInt16ToFloat32(new Int16Array(bytes.buffer));
    
    const buffer = audioContext.createBuffer(1, float32Data.length, 24000);
    buffer.getChannelData(0).set(float32Data);

    const source = audioContext.createBufferSource();
    source.buffer = buffer;
    source.connect(audioContext.destination);

    const currentTime = audioContext.currentTime;
    
    if (nextStartTime < currentTime) nextStartTime = currentTime;
    
    source.start(nextStartTime);
    nextStartTime += buffer.duration;

    audioQueue.push(source);
    
    source.onended = () => {
        const index = audioQueue.indexOf(source);
        if (index > -1) {
            audioQueue.splice(index, 1);
        }
    };
}

function stopAudioPlayback() {
    if (audioQueue.length > 0) {
        audioQueue.forEach(source => {
            try { source.stop(); } catch(e) {}
        });
        audioQueue = [];
    }
    if (audioContext) {
        nextStartTime = audioContext.currentTime;
    }
}

/**
 * Admin Menu Functions
 */
function showAdminMenu() {
    const adminMenu = document.getElementById('admin-menu');
    if (adminMenu) {
        adminMenu.classList.remove('hidden');

        // Setup dropdown toggle
        const dropdownBtn = document.getElementById('admin-dropdown-btn');
        const dropdown = document.getElementById('admin-dropdown');

        if (dropdownBtn && dropdown) {
            dropdownBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                dropdown.classList.toggle('hidden');
            });

            // Close dropdown when clicking outside
            document.addEventListener('click', (e) => {
                if (!adminMenu.contains(e.target)) {
                    dropdown.classList.add('hidden');
                }
            });
        }
    }
}

function openAdminTool(tool) {
    const baseUrl = window.location.origin;
    const orgId = localStorage.getItem('user_org');
    const username = localStorage.getItem('chat_user_id');
    const isAdmin = localStorage.getItem('user_isadmin');

    // Pass auth data via localStorage (accessible in new tab)
    localStorage.setItem('admin_org_id', orgId);
    localStorage.setItem('admin_username', username);
    localStorage.setItem('admin_authenticated', isAdmin);

    let url;
    if (tool === 'prompt_trainer') {
        url = `${baseUrl}/prompt-admin`;
    } else if (tool === 'prompt_evaluator') {
        url = `${baseUrl}/prompt-evaluator`;
    }

    // Open in new tab
    if (url) {
        window.open(url, '_blank');
    }
}

/**
 * Event Listeners
 */
sendBtn.addEventListener('click', sendMessage);

micBtn.addEventListener('click', () => {
    startVoiceSession();
});

userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

uploadBtn.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', handleUpload);