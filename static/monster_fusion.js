document.addEventListener("DOMContentLoaded", () => {
    // --- DOM Elements ---
    const status = document.getElementById("status");
    const partsList = document.getElementById("parts-list");
    const monsterDisplay = document.getElementById("monster-display");
    const apiSelect = document.getElementById("api-select");
    const generateBtn = document.getElementById("generate-btn");

    // --- State ---
    let socket;

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
            case "parts_update":
                updatePartsList(data.parts);
                break;
            case "monster_generated":
                displayMonster(data.image_url, data.prompt);
                status.textContent = "Monster generated successfully!";
                generateBtn.disabled = false;
                break;
            case "status_update":
                status.textContent = data.message;
                break;
            case "generation_error":
                alert(data.message);
                generateBtn.disabled = false;
                break;
        }
    }

    generateBtn.addEventListener('click', () => {
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

    function displayMonster(imageUrl, prompt) {
        monsterDisplay.innerHTML = `<img src="${imageUrl}" alt="${prompt}" style="max-width: 100%; border-radius: 8px;">`;
    }

    // --- Initialization ---
    connect();
});
