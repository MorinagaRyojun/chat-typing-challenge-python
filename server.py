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
    config = None

# --- App Setup ---
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/generated_monsters", StaticFiles(directory="generated_monsters"), name="generated_monsters")
templates = Jinja2Templates(directory="templates")

# --- In-memory storage for state ---
class ConnectionManager:
    def __init__(self):
        self.connections: Dict[str, List[WebSocket]] = {}
    async def connect(self, websocket: WebSocket, group: str):
        await websocket.accept()
        if group not in self.connections: self.connections[group] = []
        self.connections[group].append(websocket)
    def disconnect(self, websocket: WebSocket, group: str):
        if group in self.connections: self.connections[group].remove(websocket)
    async def broadcast(self, message: dict, group: Optional[str] = None):
        if group and group in self.connections:
            for connection in self.connections[group]: await connection.send_json(message)
        elif group is None:
            for group_name in self.connections:
                for connection in self.connections[group_name]: await connection.send_json(message)

manager = ConnectionManager()
tiktok_client: Optional[TikTokLiveClient] = None
game_instances: Dict[str, Any] = {}
chat_participants: Dict[str, str] = {} # {unique_id: nickname}
tiktok_username: Optional[str] = None

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
    return templates.TemplateResponse(f"{game_name}.html", {"request": request, "game_name": game_name})

# --- WebSocket Endpoints ---
@app.websocket("/ws/hub")
async def websocket_hub_endpoint(websocket: WebSocket):
    global tiktok_client, tiktok_username
    await manager.connect(websocket, "hub")
    try:
        while True:
            data = await websocket.receive_json()
            if data["type"] == "connect_tiktok":
                username = data.get("username")
                if username and tiktok_client is None:
                    tiktok_username = username
                    await manager.broadcast({"type": "tiktok_connection_status", "status": "connecting", "message": f"Connecting to {username}..."})
                    tiktok_client = TikTokLiveClient(unique_id=username)
                    tiktok_client.add_listener(ConnectEvent, on_connect)
                    tiktok_client.add_listener(CommentEvent, on_comment)
                    asyncio.create_task(tiktok_client.start())
    except WebSocketDisconnect:
        manager.disconnect(websocket, "hub")

@app.websocket("/ws/{game_name}")
async def websocket_game_endpoint(websocket: WebSocket, game_name: str):
    game = get_game_instance(game_name)
    if not game:
        await websocket.close(code=1011, reason="Game not found")
        return

    await manager.connect(websocket, game_name)
    try:
        # Send initial state
        await websocket.send_json({"type": "leaderboard_update", "leaderboard": game.get_leaderboard_data()})
        await websocket.send_json({"type": "participants_update", "participants": list(chat_participants.values())})

        while True:
            data = await websocket.receive_json()
            if game_name == "typing_challenge":
                if data["type"] == "start_round":
                    if not game.round_active: asyncio.create_task(game.start_new_round())
                elif data["type"] == "set_game_mode": await game.set_game_mode(data["mode"])
                elif data["type"] == "reset_leaderboard": await game.reset_leaderboard()
            elif game_name == "monster_fusion":
                if data["type"] == "generate_monster": await game.generate_monster(data["api"])
    except WebSocketDisconnect:
        manager.disconnect(websocket, game_name)
        print(f"UI for {game_name} disconnected.")
    except Exception as e:
        print(f"An error occurred in websocket for {game_name}: {e}")

# --- TikTok Event Handlers ---
async def on_connect(event: ConnectEvent):
    global chat_participants
    chat_participants.clear() # Clear participants for new session
    print(f"Successfully connected to @{event.unique_id}")
    await manager.broadcast({"type": "tiktok_connection_status", "status": "connected", "message": f"Connected to @{event.unique_id}"})
    await manager.broadcast({"type": "participants_update", "participants": []})

async def on_comment(event: CommentEvent):
    # Broadcast the raw chat message to all UIs for the live chat log
    await manager.broadcast({
        "type": "chat_message",
        "user": event.user.nickname,
        "comment": event.comment
    })

    # Add user to participants list if they are new
    is_new_participant = event.user.unique_id not in chat_participants
    chat_participants[event.user.unique_id] = event.user.nickname

    if is_new_participant:
        await manager.broadcast({
            "type": "participants_update",
            "participants": list(chat_participants.values())
        })

    # Route comment to all active game instances
    for game in game_instances.values():
        if hasattr(game, 'handle_comment'):
            asyncio.create_task(game.handle_comment(event.comment))

# --- Server Lifecycle ---
@app.on_event("startup")
async def startup_event():
    print("FastAPI server started. Navigate to http://localhost:8000")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
