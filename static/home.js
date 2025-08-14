document.addEventListener("DOMContentLoaded", () => {
    // --- DOM Elements ---
    const statusLight = document.getElementById("tiktok-status-light");
    const statusText = document.getElementById("tiktok-status-text");
    const usernameInput = document.getElementById("tiktok-username");
    const connectBtn = document.getElementById("connect-btn");

    // --- State ---
    let socket;

    // --- WebSocket Connection ---
    function connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const wsUrl = `${protocol}//${host}/ws/hub`;

        socket = new WebSocket(wsUrl);

        socket.onopen = () => {
            console.log("Connected to Hub WebSocket.");
            updateStatus("disconnected", "Disconnected");
        };

        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleServerMessage(data);
        };

        socket.onclose = () => {
            updateStatus("disconnected", "Server Connection Lost");
            setTimeout(connect, 3000); // Try to reconnect
        };
    }

    function send(data) {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify(data));
        }
    }

    // --- Event Handlers ---
    function handleServerMessage(data) {
        if (data.type === "tiktok_connection_status") {
            updateStatus(data.status, data.message);
        }
    }

    connectBtn.addEventListener('click', () => {
        const username = usernameInput.value;
        if (!username || !username.startsWith('@')) {
            alert("Please enter a valid TikTok username, starting with @.");
            return;
        }

        send({
            type: 'connect_tiktok',
            username: username
        });

        updateStatus("connecting", `Connecting to ${username}...`);
    });

    // --- UI Update Functions ---
    function updateStatus(status, message) {
        statusLight.className = ""; // Clear existing classes
        statusLight.classList.add(status); // Add new status class (e.g., 'connected')
        statusText.textContent = message;

        if (status === "connected" || status === "connecting") {
            connectBtn.disabled = true;
            usernameInput.disabled = true;
        } else {
            connectBtn.disabled = false;
            usernameInput.disabled = false;
        }
    }

    // --- Initialization ---
    connect();
});
