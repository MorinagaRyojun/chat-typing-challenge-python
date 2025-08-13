document.addEventListener("DOMContentLoaded", () => {
    // --- DOM Elements ---
    const status = document.getElementById("status");
    const announcement = document.getElementById("announcement");
    const wordLabel = document.getElementById("word-label");
    const wordToType = document.getElementById("word-to-type");
    const timer = document.getElementById("timer");
    const leaderboardBody = document.querySelector("#leaderboard tbody");

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
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        socket = new WebSocket(`${protocol}//${host}/ws`);

        socket.onopen = () => {
            status.textContent = "Connected to Game Server";
            status.style.color = "#64ffda";
        };

        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleServerMessage(data);
        };

        socket.onclose = () => {
            status.textContent = "Disconnected. Trying to reconnect...";
            status.style.color = "#ff6b6b";
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
                status.textContent = "Connected to TikTok LIVE";
                showAnnouncement("Connected to TikTok!", 3000);
                break;
            case "auto_play_status":
                isAutoPlaying = data.running;
                updateAutoPlayButton();
                break;
        }
    }

    // --- Control Panel Logic ---
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
