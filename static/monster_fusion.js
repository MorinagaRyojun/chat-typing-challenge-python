document.addEventListener("DOMContentLoaded", () => {
    // --- DOM Elements ---
    const status = document.getElementById("status");
    const partsList = document.getElementById("parts-list");
    const monsterDisplay = document.getElementById("monster-display");
    const apiSelect = document.getElementById("api-select");
    const generateBtn = document.getElementById("generate-btn");
    const loadingSpinner = document.getElementById("loading-spinner");
    const monsterPlaceholderText = document.getElementById("monster-placeholder-text");
    const participantsList = document.getElementById("participants-list");
    const chatLog = document.getElementById("chat-log");

    // --- State ---
    let socket;
    const MAX_CHAT_MESSAGES = 50;

    // --- WebSocket Connection ---
    function connect() {
        const path = window.location.pathname;
        const gameName = path.split('/')[2];

        if (!gameName) {
            status.textContent = "Error: Could not determine game name.";
            return;
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const wsUrl = `${protocol}//${host}/ws/${gameName}`;

        socket = new WebSocket(wsUrl);

        socket.onopen = () => {
            status.textContent = "Connected to Game Server.";
        };

        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleServerMessage(data);
        };

        socket.onclose = () => {
            status.textContent = "Disconnected. Please refresh.";
            generateBtn.disabled = true;
        };
    }

    function send(data) {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify(data));
        }
    }

    // --- Event Handlers ---
    function handleServerMessage(data) {
        switch (data.type) {
            case "chat_message":
                addChatMessage(data.user, data.comment);
                break;
            case "parts_update":
                updatePartsList(data.parts);
                break;
            case "participants_update":
                updateParticipantsList(data.participants);
                break;
            case "monster_generated":
                loadingSpinner.classList.add("hidden");
                displayMonster(data.image_url, data.prompt);
                status.textContent = "Monster generated successfully!";
                generateBtn.disabled = false;
                break;
            case "status_update":
                status.textContent = data.message;
                break;
            case "generation_error":
                alert(data.message);
                loadingSpinner.classList.add("hidden");
                monsterPlaceholderText.classList.remove("hidden");
                generateBtn.disabled = false;
                break;
        }
    }

    generateBtn.addEventListener('click', () => {
        monsterDisplay.innerHTML = "";
        monsterDisplay.appendChild(loadingSpinner);
        monsterDisplay.appendChild(monsterPlaceholderText);
        monsterPlaceholderText.classList.add("hidden");
        loadingSpinner.classList.remove("hidden");

        send({
            type: 'generate_monster',
            api: apiSelect.value
        });
        generateBtn.disabled = true;
        status.textContent = "Sending request to server...";
    });

    // --- UI Update Functions ---
    function updatePartsList(parts) {
        partsList.innerHTML = "";
        if (parts.length === 0) {
            partsList.innerHTML = "<li>Waiting for viewers...</li>";
        } else {
            parts.forEach(part => {
                const li = document.createElement("li");
                li.textContent = part;
                partsList.appendChild(li);
            });
        }
    }

    function updateParticipantsList(participants) {
        participantsList.innerHTML = "";
        if (participants.length === 0) {
            participantsList.innerHTML = "<li>Waiting for chatters...</li>";
        } else {
            participants.forEach(name => {
                const li = document.createElement("li");
                li.textContent = name;
                participantsList.appendChild(li);
            });
        }
    }

    function addChatMessage(user, comment) {
        // Clear initial message if it exists
        const initialMessage = chatLog.querySelector('.chat-message-system');
        if(initialMessage) initialMessage.remove();

        if (chatLog.children.length > MAX_CHAT_MESSAGES) {
            chatLog.removeChild(chatLog.firstChild);
        }
        const messageElement = document.createElement("p");
        messageElement.classList.add("chat-message");

        const userSpan = document.createElement("span");
        userSpan.classList.add("chat-message-user");
        userSpan.textContent = user;

        const textSpan = document.createElement("span");
        textSpan.classList.add("chat-message-text");
        textSpan.textContent = `: ${comment}`;

        messageElement.appendChild(userSpan);
        messageElement.appendChild(textSpan);
        chatLog.appendChild(messageElement);
        chatLog.scrollTop = chatLog.scrollHeight;
    }

    function displayMonster(imageUrl, prompt) {
        const img = document.createElement("img");
        img.src = imageUrl;
        img.alt = prompt;
        img.style.maxWidth = "100%";
        img.style.borderRadius = "8px";
        monsterDisplay.innerHTML = ""; // Clear spinner
        monsterDisplay.appendChild(img);
    }

    // --- Initialization ---
    connect();
});
