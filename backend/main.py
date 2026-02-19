from fastapi import FastAPI, HTTPException, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse
from sse_starlette.sse import EventSourceResponse
from typing import Dict, List
import asyncio
import os
import json
import uvicorn
from .game import ReversiGame, GameSettings
import uuid

app = FastAPI(title="Reversi API")

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for active games
games: Dict[str, ReversiGame] = {}
# Event bus: game_id -> list of asyncio.Queue
game_listeners: Dict[str, List[asyncio.Queue]] = {}

async def broadcast_event(game_id: str, data: dict):
    if game_id in game_listeners:
        for queue in game_listeners[game_id]:
            await queue.put(json.dumps(data))

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/game/create")
async def create_game(settings: GameSettings = Body(...)):
    game = ReversiGame(settings)
    games[game.game_id] = game
    return {"game_id": game.game_id}

@app.post("/game/{game_id}/claim")
async def claim_side(game_id: str, payload: dict = Body(...)):
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    player = payload.get("player")
    
    if player not in [game.BLACK, game.WHITE]:
        raise HTTPException(status_code=400, detail="Invalid player side")
    
    token = game.claim_side(player)
    if token is None:
        raise HTTPException(status_code=400, detail="Side already claimed")
    
    # Broadcast change
    await broadcast_event(game_id, {"type": "claim", "slots": game.get_state()["slots"]})
    
    return {"token": token, "player": player}

@app.get("/game/{game_id}")
async def get_game_state(game_id: str):
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    return games[game_id].get_state()

@app.post("/game/{game_id}/move")
async def make_move(game_id: str, payload: dict = Body(...)):
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    x = payload.get("x")
    y = payload.get("y")
    player = payload.get("player")
    token = payload.get("token")
    
    if any(v is None for v in [x, y, player, token]):
        raise HTTPException(status_code=400, detail="Missing required fields: x, y, player, token")
    
    success = game.make_move(x, y, player, token)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid move or unauthorized")
    
    state = game.get_state()
    # Broadcast move
    await broadcast_event(game_id, {"type": "move", "state": state})
    
    return state

@app.get("/game/{game_id}/events")
async def game_events(game_id: str, request: Request):
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    async def event_generator():
        queue = asyncio.Queue()
        if game_id not in game_listeners:
            game_listeners[game_id] = []
        game_listeners[game_id].append(queue)
        
        try:
            while True:
                # Check for client disconnect
                if await request.is_disconnected():
                    break
                
                data = await queue.get()
                yield {"data": data}
        finally:
            game_listeners[game_id].remove(queue)
            if not game_listeners[game_id]:
                del game_listeners[game_id]

    return EventSourceResponse(event_generator())

# Browser Routes
@app.get("/")
@app.get("/play/")
async def new_game_redirect():
    # Create a default game and redirect
    game = ReversiGame()
    games[game.game_id] = game
    return RedirectResponse(url=f"/play/{game.game_id}")

@app.get("/play/{game_id}")
async def serve_game(game_id: str):
    if game_id not in games:
        return RedirectResponse(url="/play/")
    return FileResponse("frontend/index.html")

# Serve static assets (CSS/JS)
@app.get("/{filename}")
async def get_site_files(filename: str):
    file_path = os.path.join("frontend", filename)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
