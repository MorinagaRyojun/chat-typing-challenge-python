import asyncio
import importlib
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Optional, Dict, Any

# Import the base TikTok client
from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent, ConnectEvent

# Try to import API keys from config.py
try:
    import config
except ImportError:
    config = None # Set to None if config.py doesn't exist

# --- App Setup ---
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/generated_monsters", StaticFiles(directory="generated_monsters"), name="generated_monsters")
templates = Jinja2Templates(directory="templates")

# --- In-memory storage for state ---
class ConnectionManager:
    def __init__(self):
        self.connections: Dict[str, List[WebSocket]] = {}
    async def connect(self, websocket: WebSocket, game_name: str):
        await websocket.accept()
        if game_name not in self.connections: self.connections[game_name] = []
        self.connections[game_name].append(websocket)
    def disconnect(self, websocket: WebSocket, game_name: str):
        if game_name in self.connections: self.connections[game_name].remove(websocket)
    async def broadcast(self, message: dict, game_name: str):
        if game_name in self.connections:
            for connection in self.connections[game_name]: await connection.send_json(message)

manager = ConnectionManager()
tiktok_client: Optional[TikTokLiveClient] = None
game_instances: Dict[str, Any] = {}
active_game_name: Optional[str] = None

# --- Helper function to get/create game instance ---
def get_game_instance(game_name: str):
    global game_instances
    if game_name not in game_instances:
        try:
            game_module = importlib.import_module(f"games.{game_name}")
            game_class = getattr(game_module, "Game")
            game_manager_for_game = GameConnectionManager(game_name, manager)
            game_instances[game_name] = game_class(game_manager_for_game)
            print(f"Created new instance for game: {game_name}")
        except (ImportError, AttributeError) as e:
            print(f"Could not load game '{game_name}': {e}")
            return None
    return game_instances[game_name]

class GameConnectionManager:
    def __init__(self, game_name: str, manager: ConnectionManager):
        self.game_name = game_name
        self.manager = manager
    async def broadcast(self, message: dict):
        await self.manager.broadcast(message, self.game_name)

# --- FastAPI Routes ---
@app.get("/", response_class=HTMLResponse)
async def route_home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/game/{game_name}", response_class=HTMLResponse)
async def route_game_page(request: Request, game_name: str):
    if get_game_instance(game_name) is None:
        return HTMLResponse("Game not found", status_code=404)
    template_name = f"{game_name}.html"
    return templates.TemplateResponse(template_name, {"request": request, "game_name": game_name})

@app.websocket("/ws/{game_name}")
async def websocket_endpoint(websocket: WebSocket, game_name: str):
    global active_game_name
    game = get_game_instance(game_name)
    if not game:
        await websocket.close(code=1011, reason="Game not found")
        return

    await manager.connect(websocket, game_name)
    active_game_name = game_name # Set the currently active game
    print(f"Active game is now: {active_game_name}")
    try:
        await websocket.send_json({"type": "leaderboard_update", "leaderboard": game.get_leaderboard_data()})
        while True:
            data = await websocket.receive_json()
            # Route command to the correct game logic
            if game_name == "typing_challenge":
                if data["type"] == "start_round":
                    if not game.round_active: asyncio.create_task(game.start_new_round())
                elif data["type"] == "set_game_mode": await game.set_game_mode(data["mode"])
                elif data["type"] == "reset_leaderboard": await game.reset_leaderboard()

            elif game_name == "monster_fusion":
                if data["type"] == "generate_monster":
                    await game.generate_monster(data["api"])

    except WebSocketDisconnect:
        manager.disconnect(websocket, game_name)
        print(f"UI for {game_name} disconnected.")
    except Exception as e:
        print(f"An error occurred in websocket for {game_name}: {e}")

# --- TikTok Logic ---
# TODO: Move username to a config file or get from a UI
TIKTOK_USERNAME = "@ryojun_m"
tiktok_client = TikTokLiveClient(unique_id=TIKTOK_USERNAME)

@tiktok_client.on(ConnectEvent)
async def on_connect(event: ConnectEvent):
    print(f"Successfully connected to @{event.unique_id}")
    # We can't broadcast to a specific game, so we broadcast to all
    for game_name in manager.connections.keys():
        await manager.broadcast({"type": "tiktok_connected"}, game_name=game_name)

@tiktok_client.on(CommentEvent)
async def on_comment(event: CommentEvent):
    if active_game_name and active_game_name in game_instances:
        active_game = game_instances[active_game_name]
        if hasattr(active_game, 'handle_comment'):
             await active_game.handle_comment(event.comment)

@app.on_event("startup")
async def startup_event():
    print("FastAPI server started. Navigate to http://localhost:8000")
    print("Attempting to connect to TikTok...")
    asyncio.create_task(tiktok_client.start())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
