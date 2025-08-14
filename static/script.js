document.addEventListener("DOMContentLoaded", () => {
    // --- DOM Elements ---
    const status = document.getElementById("status");
    const announcement = document.getElementById("announcement");
    const wordLabel = document.getElementById("word-label");
    const wordToType = document.getElementById("word-to-type");
    const timer = document.getElementById("timer");
    const leaderboardBody = document.querySelector("#leaderboard tbody");
    const connectTiktokBtn = document.getElementById("connect-tiktok-btn");

    // Control Panel Elements
    const gameModeSelect = document.getElementById("game-mode-select");
    const modeManualRadio = document.getElementById("mode-manual");
    const modeAutoRadio = document.getElementById("mode-auto");
    const manualControls = document.getElementById("manual-controls");
    const autoControls = document.getElementById("auto-controls");
    const startRoundBtn = document.getElementById("start-round-btn");
    const autoDelayInput = document.getElementById("auto-delay-input");
    const toggleAutoPlayBtn = document.getElementById("toggle-auto-play-btn");
    const resetLeaderboardBtn = document.getElementById("reset-leaderboard-btn");

    // --- State ---
    let socket;
    let isAutoPlaying = false;

    // --- WebSocket Connection ---
    function connect() {
        const path = window.location.pathname;
        const gameName = path.split('/')[2];

        if (!gameName) {
            status.textContent = "Error: Could not determine game name from URL.";
            return;
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const wsUrl = `${protocol}//${host}/ws/${gameName}`;

        socket = new WebSocket(wsUrl);

        socket.onopen = () => {
            status.textContent = "Connected to Game Server. Ready to connect to TikTok.";
            status.style.color = "#64ffda";
            connectTiktokBtn.disabled = false;
        };

        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleServerMessage(data);
        };

        socket.onclose = () => {
            status.textContent = "Disconnected. Trying to reconnect...";
            status.style.color = "#ff6b6b";
            connectTiktokBtn.disabled = true;
            isAutoPlaying = false;
            updateAutoPlayButton();
            setTimeout(connect, 3000);
        };

        socket.onerror = (error) => {
            console.error("WebSocket Error:", error);
            status.textContent = "Connection Error";
        };
    }

    function send(data) {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify(data));
        } else {
            console.error("WebSocket is not connected.");
        }
    }

    // --- Event Handlers ---
    function handleServerMessage(data) {
        switch (data.type) {
            case "new_round":
                wordLabel.textContent = data.mode === 'Hard' ? "Unscramble this:" : "Type this:";
                wordToType.textContent = data.word;
                timer.textContent = data.round_time;
                showAnnouncement(`New Round: ${data.mode}`, 3000);
                break;
            case "timer_update":
                timer.textContent = data.time;
                break;
            case "round_over":
                let winnerText = "Round Over! ";
                if (data.winners.length > 0) {
                    const winnerNames = data.winners.map(w => w.nickname).join(', ');
                    winnerText += `Winners: ${winnerNames}`;
                } else {
                    winnerText += "No winners this round.";
                }
                showAnnouncement(winnerText, 5000);
                break;
            case "leaderboard_update":
                updateLeaderboard(data.leaderboard);
                break;
            case "tiktok_connected":
                status.textContent = "Connected to TikTok LIVE!";
                status.style.color = "#25d366"; // A nice green
                connectTiktokBtn.style.display = 'none'; // Hide button after connecting
                break;
            case "status_update":
                status.textContent = data.message;
                break;
            case "auto_play_status":
                isAutoPlaying = data.running;
                updateAutoPlayButton();
                break;
        }
    }

    // --- Control Panel Logic ---
    connectTiktokBtn.addEventListener('click', () => {
        send({ type: 'connect_tiktok' });
        connectTiktokBtn.disabled = true;
        status.textContent = "Attempting to connect to TikTok...";
    });

    modeManualRadio.addEventListener('change', () => {
        manualControls.classList.remove('hidden');
        autoControls.classList.add('hidden');
    });

    modeAutoRadio.addEventListener('change', () => {
        manualControls.classList.add('hidden');
        autoControls.classList.remove('hidden');
    });

    gameModeSelect.addEventListener('change', (e) => {
        send({ type: 'set_game_mode', mode: e.target.value });
    });

    startRoundBtn.addEventListener('click', () => {
        send({ type: 'start_round' });
    });

    toggleAutoPlayBtn.addEventListener('click', () => {
        if (isAutoPlaying) {
            send({ type: 'stop_auto_play' });
        } else {
            const delay = parseInt(autoDelayInput.value, 10) || 15;
            send({ type: 'start_auto_play', delay: delay });
        }
    });

    resetLeaderboardBtn.addEventListener('click', () => {
        if (confirm("Are you sure you want to reset the leaderboard?")) {
            send({ type: 'reset_leaderboard' });
        }
    });

    function updateAutoPlayButton() {
        if (isAutoPlaying) {
            toggleAutoPlayBtn.textContent = "Stop Auto-Play";
            toggleAutoPlayBtn.style.backgroundColor = "#ff6b6b";
        } else {
            toggleAutoPlayBtn.textContent = "Start Auto-Play";
            toggleAutoPlayBtn.style.backgroundColor = "#64ffda";
        }
    }

    // --- UI Update Functions ---
    function updateLeaderboard(leaderboardData) {
        leaderboardBody.innerHTML = "";
        if (leaderboardData.length === 0) {
            leaderboardBody.innerHTML = '<tr><td colspan="3">No players yet...</td></tr>';
        } else {
            leaderboardData.forEach((player, index) => {
                const row = document.createElement("tr");
                row.innerHTML = `
                    <td>#${index + 1}</td>
                    <td>${player.nickname}</td>
                    <td>${player.score}</td>
                `;
                leaderboardBody.appendChild(row);
            });
        }
    }

    function showAnnouncement(message, duration) {
        announcement.textContent = message;
        announcement.style.display = 'block';
        setTimeout(() => {
            announcement.style.display = 'none';
        }, duration);
    }

    // --- Initializations ---
    connect();
});
