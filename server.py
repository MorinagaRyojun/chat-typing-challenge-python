import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
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
auto_play_task = None

# --- Game Control Functions ---
async def run_auto_play_loop(delay: int):
    """The main loop for automatic game rounds."""
    while True:
        await game.start_new_round()
        await manager.broadcast({"type": "auto_play_status", "running": True, "delay": delay})
        await asyncio.sleep(delay)

# --- FastAPI Routes ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global auto_play_task
    await manager.connect(websocket)
    try:
        await websocket.send_json({
            "type": "leaderboard_update",
            "leaderboard": game.get_leaderboard_data()
        })
        while True:
            data = await websocket.receive_json()

            # Route commands from the UI
            if data["type"] == "start_round":
                if not game.round_active:
                    asyncio.create_task(game.start_new_round())

            elif data["type"] == "set_game_mode":
                await game.set_game_mode(data["mode"])

            elif data["type"] == "reset_leaderboard":
                await game.reset_leaderboard()

            elif data["type"] == "start_auto_play":
                if auto_play_task is None or auto_play_task.done():
                    delay = int(data.get("delay", 15))
                    auto_play_task = asyncio.create_task(run_auto_play_loop(delay))
                    await manager.broadcast({"type": "auto_play_status", "running": True, "delay": delay})

            elif data["type"] == "stop_auto_play":
                if auto_play_task and not auto_play_task.done():
                    auto_play_task.cancel()
                    auto_play_task = None
                await manager.broadcast({"type": "auto_play_status", "running": False})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("UI disconnected.")
    except Exception as e:
        print(f"An error occurred in websocket: {e}")


# --- TikTok Event Handlers ---
@tiktok_client.on(ConnectEvent)
async def on_connect(event: ConnectEvent):
    print(f"Successfully connected to @{event.unique_id} (Room ID: {tiktok_client.room_id})")
    await manager.broadcast({"type": "tiktok_connected"})

@tiktok_client.on(CommentEvent)
async def on_comment(event: CommentEvent):
    await game.check_answer(user_id=event.user.unique_id, nickname=event.user.nickname, comment=event.comment)


# --- FastAPI Startup Event ---
@app.on_event("startup")
async def startup_event():
    print("FastAPI server started. Attempting to connect to TikTok...")
    asyncio.create_task(tiktok_client.start())

if __name__ == "__main__":
    import uvicorn
    game.game_mode = "classic"
    print("Starting server with Uvicorn.")
    uvicorn.run(app, host="0.0.0.0", port=8000)
