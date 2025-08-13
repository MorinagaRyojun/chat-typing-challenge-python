import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List

# Import the game logic and TikTok client
from game_logic import Game
from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent, ConnectEvent

# --- Configuration ---
TIKTOK_USERNAME = "@ryojun_m"

# --- FastAPI App Setup ---
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- WebSocket Connection Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

# --- Game and TikTok Client Setup ---
game = Game(manager)
tiktok_client: TikTokLiveClient = TikTokLiveClient(unique_id=TIKTOK_USERNAME)

# --- FastAPI Routes ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send the initial leaderboard state when a new UI connects
        await websocket.send_json({
            "type": "leaderboard_update",
            "leaderboard": game.get_leaderboard_data()
        })
        while True:
            # Keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("UI disconnected.")

# --- TikTok Event Handlers ---
@tiktok_client.on(ConnectEvent)
async def on_connect(event: ConnectEvent):
    print(f"Successfully connected to @{event.unique_id} (Room ID: {tiktok_client.room_id})")
    await manager.broadcast({"type": "tiktok_connected"})
    # Start the game loop once connected
    asyncio.create_task(run_game_loop())

@tiktok_client.on(CommentEvent)
async def on_comment(event: CommentEvent):
    # Pass the comment to the game logic
    await game.check_answer(user_id=event.user.unique_id, nickname=event.user.nickname, comment=event.comment)

# --- Game Loop ---
async def run_game_loop():
    await asyncio.sleep(5)
    while True:
        await game.start_new_round()
        await asyncio.sleep(15) # Wait before starting the next round

# --- FastAPI Startup Event ---
@app.on_event("startup")
async def startup_event():
    print("FastAPI server started. Attempting to connect to TikTok...")
    # Start the TikTok client in the background
    asyncio.create_task(tiktok_client.start())

if __name__ == "__main__":
    import uvicorn
    # --- Game Configuration ---
    # You can change the game mode here before starting the server.
    game.game_mode = "classic"

    if game.game_mode == "speed_up":
        game.round_time_seconds = game.speed_up_start_time

    print("Starting server with Uvicorn.")
    print(f"Selected Game Mode: {game.game_mode.capitalize()}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
