import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Optional

# Import the game logic and TikTok client
from game_logic import Game
from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent, ConnectEvent

# --- App Setup ---
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- In-memory storage for settings and state ---
game_settings = {
    "username": None,
    "game_mode": "classic"
}
tiktok_client: Optional[TikTokLiveClient] = None
auto_play_task = None

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
game = Game(manager)

# --- FastAPI Routes ---
@app.get("/", response_class=HTMLResponse)
async def route_settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})

@app.post("/settings")
async def handle_settings_form(username: str = Form(...), game_mode: str = Form(...)):
    game_settings["username"] = username
    game_settings["game_mode"] = game_mode
    await game.set_game_mode(game_mode)
    return RedirectResponse(url="/game", status_code=303)

@app.get("/game", response_class=HTMLResponse)
async def route_game_page(request: Request):
    return templates.TemplateResponse("game.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global auto_play_task, tiktok_client
    await manager.connect(websocket)
    try:
        # Send initial state
        await websocket.send_json({"type": "leaderboard_update", "leaderboard": game.get_leaderboard_data()})
        await websocket.send_json({"type": "game_mode_changed", "mode": game.game_mode})

        while True:
            data = await websocket.receive_json()
            if data["type"] == "connect_tiktok":
                if tiktok_client is None and game_settings["username"]:
                    await manager.broadcast({"type": "status_update", "message": f"Connecting to {game_settings['username']}..."})

                    # Define handlers here to close over the current game and manager instances
                    @TikTokLive.on(ConnectEvent)
                    async def on_connect(event: ConnectEvent):
                        print(f"Successfully connected to @{event.unique_id}")
                        await manager.broadcast({"type": "tiktok_connected"})

                    @TikTokLive.on(CommentEvent)
                    async def on_comment(event: CommentEvent):
                        await game.check_answer(user_id=event.user.unique_id, nickname=event.user.nickname, comment=event.comment)

                    tiktok_client = TikTokLiveClient(unique_id=game_settings["username"])
                    tiktok_client.add_listener(ConnectEvent, on_connect)
                    tiktok_client.add_listener(CommentEvent, on_comment)

                    asyncio.create_task(tiktok_client.start())

            elif data["type"] == "start_round":
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

# --- Game Control Functions ---
async def run_auto_play_loop(delay: int):
    """The main loop for automatic game rounds."""
    while True:
        await game.start_new_round()
        await manager.broadcast({"type": "auto_play_status", "running": True, "delay": delay})
        await asyncio.sleep(delay)

if __name__ == "__main__":
    import uvicorn
    print("Starting server with Uvicorn. Navigate to http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
