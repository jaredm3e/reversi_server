"""
Reversi AI Agent Example (Greedy Strategy)

This script serves as a reference implementation for building AI agents that
interact with the Reversi Game API. It demonstrates:
1. Side claiming (authentication)
2. State polling & move validation
3. Real-time event handling via Server-Sent Events (SSE)
4. Basic greedy decision making
"""

import requests
import time
import sys
import argparse
import json

class GreedyAI:
    def __init__(self, api_url, game_id, player_side):
        """
        Initialize the AI agent.
        :param api_url: The base URL of the Reversi server (e.g., http://localhost:8000)
        :param game_id: The unique ID (UUID) of the game session to join
        :param player_side: The side to play (1 for Black, 2 for White)
        """
        self.api_url = api_url.rstrip('/')
        self.game_id = game_id
        self.player_side = player_side
        self.token = None  # Secured token received after claiming a side

    def claim_side(self):
        """
        Attempts to claim a player slot (Black or White) for a specific game.
        If successful, it stores the 'token' required for future moves.
        """
        print(f"[*] Attempting to claim side {self.player_side} for game {self.game_id}...")
        try:
            # POST /game/{id}/claim | Payload: {"player": int}
            resp = requests.post(f"{self.api_url}/game/{self.game_id}/claim", json={"player": self.player_side})
            if resp.status_code == 200:
                data = resp.json()
                self.token = data["token"]
                print(f"[+] Successfully claimed side. Authorized token acquired.")
                return True
            else:
                print(f"[-] Claim failed: {resp.json().get('detail', 'Unknown error')}")
                return False
        except Exception as e:
            print(f"[!] Connection error during claim: {e}")
            return False

    def get_state(self):
        """
        Fetches the current full game state from the API.
        :return: JSON object containing board, turns, scores, etc.
        """
        try:
            # GET /game/{id}
            resp = requests.get(f"{self.api_url}/game/{self.game_id}")
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"[!] State fetch error: {e}")
        return None

    def find_best_move(self, state):
        """
        Analyzes the current state and returns the move that maximizes immediate captures.
        This is a simple 'Greedy' heuristic.
        """
        board = state["board"]
        valid_moves = state["valid_moves"] # The API provides a list of valid moves (x, y)
        if not valid_moves:
            return None
        
        best_move = valid_moves[0]
        max_flips = -1
        
        for x, y in valid_moves:
            # We calculate how many pieces would be flipped if we move here
            flips = self.count_flips(board, x, y, self.player_side)
            if flips > max_flips:
                max_flips = flips
                best_move = (x, y)
        
        return best_move

    def count_flips(self, board, x, y, player):
        """
        Simulates move logic to count captures.
        """
        opponent = 2 if player == 1 else 1
        directions = [
            (0, -1), (1, -1), (1, 0), (1, 1),
            (0, 1), (-1, 1), (-1, 0), (-1, -1)
        ]
        
        total_flips = 0
        for dx, dy in directions:
            count = 0
            nx, ny = x + dx, y + dy
            # Travel in direction while seeing opponent pieces
            while 0 <= nx < 8 and 0 <= ny < 8 and board[ny][nx] == opponent:
                count += 1
                nx += dx
                ny += dy
            
            # If we hit our own piece at the end, the chain is valid
            if 0 <= nx < 8 and 0 <= ny < 8 and board[ny][nx] == player:
                total_flips += count
        return total_flips

    def make_move(self, x, y):
        """
        Sends the move command to the API.
        Requires the authorized token acquired during claim_side.
        """
        print(f"[*] AI moving to ({x}, {y})...")
        try:
            # POST /game/{id}/move | Payload: {"x": int, "y": int, "player": int, "token": str}
            resp = requests.post(
                f"{self.api_url}/game/{self.game_id}/move",
                json={"x": x, "y": y, "player": self.player_side, "token": self.token}
            )
            if resp.status_code == 200:
                print("[+] Move successful.")
                return True
            else:
                print(f"[-] Move failed: {resp.json().get('detail', 'Unknown error')}")
        except Exception as e:
            print(f"[!] Move execution error: {e}")
        return False

    def run(self):
        """
        Main execution loop. Uses Server-Sent Events (SSE) for real-time turn monitoring.
        This allows the AI to react instantly without heavy polling.
        """
        if not self.claim_side():
            return
        
        role = 'Black' if self.player_side == 1 else 'White'
        print(f"[*] AI ({role}) is active and listening for events...")
        
        # 1. Initial State Check: Check if it's already our turn
        state = self.get_state()
        if state and state["current_turn"] == self.player_side:
            self.play_turn(state)

        # 2. Event Loop: Listen for real-time game updates via SSE
        url = f"{self.api_url}/game/{self.game_id}/events"
        try:
            # We use stream=True to process the long-running HTTP connection
            response = requests.get(url, stream=True)
            for line in response.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    if decoded.startswith('data: '):
                        # Parse the SSE 'data' field
                        event_data = json.loads(decoded[6:])
                        
                        # We only care about 'move' events which signal a change in turn
                        if event_data.get("type") == "move":
                            state = event_data["state"]
                            if not state["is_over"] and state["current_turn"] == self.player_side:
                                self.play_turn(state)
        except Exception as e:
            print(f"[!] SSE connection lost ({e}). Falling back to manual polling.")
            # Fallback to standard polling if SSE fails
            while True:
                state = self.get_state()
                if state and not state["is_over"] and state["current_turn"] == self.player_side:
                    self.play_turn(state)
                time.sleep(1)

    def play_turn(self, state):
        """
        Calculates and executes the best move for the current state.
        """
        move = self.find_best_move(state)
        if move:
            self.make_move(move[0], move[1])
        else:
             print("[*] No valid moves available (passing turn).")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Educational Reversi AI Agent")
    parser.add_argument("game_id", help="UUID of the game session")
    parser.add_argument("--side", type=int, choices=[1, 2], default=2, help="1 for Black, 2 for White")
    parser.add_argument("--url", default="http://localhost:8000", help="API server URL")
    
    args = parser.parse_args()
    
    ai = GreedyAI(args.url, args.game_id, args.side)
    ai.run()
