# Premium Reversi Game

A full-stack Reversi (Othello) game featuring a FastAPI backend and a premium glassmorphism web frontend. Supports multi-game routing, side claiming, and autonomous AI agents.

## Features

- **Multi-Game Routing**: Unique URLs for every game session (`/play/<uuid>`).
- **Side Claiming**: Dynamic slot management for Black and White players.
- **Security**: Secret tokens for each player to prevent unauthorized moves.
- **Premium UI**: Modern, responsive design with valid move hints and smooth transitions.
- **AI Support**: Standalone Greedy AI agent that connects via the standard API.

## Setup

1. **Prerequisites**: Ensure you have Python 3.10+ installed.
2. **Virtual Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

### 1. Start the Server
Run the FastAPI backend from the project root:
```bash
python3 -m backend.main
```
The server will be available at `http://localhost:8000`.

### 2. Play as a Human
- Open your browser and navigate to `http://localhost:8000/`.
- You will be automatically redirected to a new game URL.
- Click **Join as Black** or **Join as White** to take control of a side.
- Share the URL with a friend to play together!

### 3. Connect the AI Agent
You can run the Greedy AI agent to play against a human or another AI:
```bash
# To play as White (Side 2) in a specific game:
python3 backend/ai_player.py <GAME_ID> --side 2
```
To find the `<GAME_ID>`, simply copy the UUID from your browser's URL (e.g., in `/play/f47ac10b...`, the ID is `f47ac10b...`).

## Technical Overview

### Project Structure
- `backend/main.py`: FastAPI server and routing.
- `backend/game.py`: Core Reversi logic and state management.
- `backend/ai_player.py`: Standalone AI script.
- `frontend/`: HTML, CSS, and Vanilla JS assets.
- `tests/`: Logic verification suite.

### Core API Endpoints
- `GET /play/`: Creates a new game and redirects.
- `POST /game/{id}/claim`: Claim a side (Black=1, White=2) and receive a session token.
- `POST /game/{id}/move`: Submit a move with a valid token.
- `GET /game/{id}`: Fetch current board state and player slot availability.

## AI Development Guide

Developers wishing to create new AI agents should follow this workflow:

### 1. Game State Schema (`GET /game/{id}`)
Returns a JSON object with:
- `board`: 8x8 list of lists. `0=Empty`, `1=Black`, `2=White`.
- `current_turn`: `1` (Black) or `2` (White).
- `scores`: `{"black": N, "white": M}`.
- `valid_moves`: List of `[x, y]` coordinates.
- `slots`: `{"black": "open"|"filled", "white": "open"|"filled"}`. Use this to find available sides.
- `is_over`: Boolean.
- `winner`: `1`, `2`, or `0` (Tie).

### 2. Side Claiming (`POST /game/{id}/claim`)
Body: `{"player": 1|2}`
Returns: `{"token": "uuid", "player": 1|2}`
> [!IMPORTANT]
> The `token` is required for all move requests. If the side is already claimed, the server returns `400 Bad Request`.

### 3. Move Submission (`POST /game/{id}/move`)
Body: `{"x": int, "y": int, "player": 1|2, "token": "uuid"}`
Returns: The updated game state after the move is processed.

- **Turn Logic**: Check `state["current_turn"] == my_side`.
- **Coordinate System**: `(0,0)` is the top-left corner. `x` is horizontal, `y` is vertical.

### 4. Real-time Notifications (SSE)
Instead of polling, agents should use the Server-Sent Events (SSE) endpoint:
`GET /game/{id}/events`

The stream broadcasts JSON events:
- **Move Event**: `{"type": "move", "state": {...}}`. Triggered whenever any player makes a valid move.
- **Claim Event**: `{"type": "claim", "slots": {...}}`. Triggered when a player claims a side.

Using SSE allows for instant reactions and "super fast" automated gameplay.

## Game Rules
Reversi is a strategy board game for two players. The goal is to have the majority of your color pieces on the board at the end of the game.
- Moves must "flank" at least one opponent piece in any of the 8 directions.
- Flanked pieces are flipped to the current player's color.
- If a player cannot move, they pass. If neither can move, the game ends.
