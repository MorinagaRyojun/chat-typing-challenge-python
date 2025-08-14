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

# --- App Setup ---
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- In-memory storage for state ---
# We will have one manager for all websocket connections
# and one TikTok client that can be shared across games.
# We will also store one instance of each game.
class ConnectionManager:
    def __init__(self):
        self.connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, game_name: str):
        await websocket.accept()
        if game_name not in self.connections:
            self.connections[game_name] = []
        self.connections[game_name].append(websocket)

    def disconnect(self, websocket: WebSocket, game_name: str):
        if game_name in self.connections:
            self.connections[game_name].remove(websocket)

    async def broadcast(self, message: dict, game_name: str):
        if game_name in self.connections:
            for connection in self.connections[game_name]:
                await connection.send_json(message)

manager = ConnectionManager()
tiktok_client: Optional[TikTokLiveClient] = None
game_instances: Dict[str, Any] = {}

# --- Helper function to get/create game instance ---
def get_game_instance(game_name: str):
    if game_name not in game_instances:
        try:
            game_module = importlib.import_module(f"games.{game_name}")
            game_class = getattr(game_module, "Game")
            # Pass a reference to the manager that is specific to this game
            game_manager_for_game = GameConnectionManager(game_name, manager)
            game_instances[game_name] = game_class(game_manager_for_game)
            print(f"Created new instance for game: {game_name}")
        except (ImportError, AttributeError) as e:
            print(f"Could not load game '{game_name}': {e}")
            return None
    return game_instances[game_name]

# A wrapper to give each game a simple broadcast method
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
    game_instance = get_game_instance(game_name)
    if not game_instance:
        return HTMLResponse("Game not found", status_code=404)
    return templates.TemplateResponse(f"{game_name}.html", {"request": request, "game_name": game_name})

@app.websocket("/ws/{game_name}")
async def websocket_endpoint(websocket: WebSocket, game_name: str):
    game = get_game_instance(game_name)
    if not game:
        await websocket.close(code=1011, reason="Game not found")
        return

    await manager.connect(websocket, game_name)
    try:
        # Send initial state
        await websocket.send_json({"type": "leaderboard_update", "leaderboard": game.get_leaderboard_data()})

        while True:
            # For now, we only receive commands for the typing challenge.
            # This will need to be refactored further for the monster game.
            data = await websocket.receive_json()
            if game_name == "typing_challenge":
                if data["type"] == "start_round":
                    if not game.round_active:
                        asyncio.create_task(game.start_new_round())
                # ... other typing_challenge commands
                elif data["type"] == "set_game_mode":
                    await game.set_game_mode(data["mode"])
                elif data["type"] == "reset_leaderboard":
                    await game.reset_leaderboard()

    except WebSocketDisconnect:
        manager.disconnect(websocket, game_name)
        print(f"UI for {game_name} disconnected.")
    except Exception as e:
        print(f"An error occurred in websocket for {game_name}: {e}")

# --- TikTok Logic (Simplified for now) ---
# This part needs a UI to trigger the connection
# For now, we'll leave it uninitialized.
# A "Connect" button on the home page or per-game page would be needed.

@app.on_event("startup")
async def startup_event():
    print("FastAPI server started. Navigate to http://localhost:8000")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
