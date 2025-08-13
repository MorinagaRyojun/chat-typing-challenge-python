document.addEventListener("DOMContentLoaded", () => {
    const status = document.getElementById("status");
    const announcement = document.getElementById("announcement");
    const wordLabel = document.getElementById("word-label");
    const wordToType = document.getElementById("word-to-type");
    const timer = document.getElementById("timer");
    const leaderboardBody = document.querySelector("#leaderboard tbody");

    let socket;

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
            setTimeout(connect, 3000); // Try to reconnect every 3 seconds
        };

        socket.onerror = (error) => {
            console.error("WebSocket Error:", error);
            status.textContent = "Connection Error";
            status.style.color = "#ff6b6b";
        };
    }

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
            case "correct_answer":
                // Maybe a small visual cue in the future
                console.log(`${data.nickname} got it right!`);
                break;
            case "tiktok_connected":
                status.textContent = "Connected to TikTok LIVE";
                break;
        }
    }

    function updateLeaderboard(leaderboardData) {
        leaderboardBody.innerHTML = ""; // Clear existing rows
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

    connect();
});
