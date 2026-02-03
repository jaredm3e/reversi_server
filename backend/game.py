import time
from typing import List, Tuple, Optional
from pydantic import BaseModel, Field
import uuid

class Move(BaseModel):
    x: int
    y: int
    player: int  # 1 for Black, 2 for White

class GameSettings(BaseModel):
    turn_cooldown: float = 0.0  # Seconds to wait between moves
    black_is_human: bool = True
    white_is_human: bool = True

class ReversiGame:
    BLACK = 1
    WHITE = 2
    EMPTY = 0

    def __init__(self, settings: GameSettings = GameSettings()):
        self.game_id = str(uuid.uuid4())
        self.black_token = None
        self.white_token = None
        self.settings = settings
        
        # Initialize board
        self.board = [[self.EMPTY for _ in range(8)] for _ in range(8)]
        # Starting pieces
        self.board[3][3] = self.WHITE
        self.board[3][4] = self.BLACK
        self.board[4][3] = self.BLACK
        self.board[4][4] = self.WHITE
        
        self.current_turn = self.BLACK
        self.last_move_time = 0.0
        self.history = []
        self.is_over = False
        self.winner = None

    def get_state(self):
        return {
            "game_id": self.game_id,
            "board": self.board,
            "current_turn": self.current_turn,
            "is_over": self.is_over,
            "winner": self.winner,
            "scores": self.get_scores(),
            "valid_moves": self.get_valid_moves(self.current_turn),
            "slots": {
                "black": "open" if self.black_token is None else "filled",
                "white": "open" if self.white_token is None else "filled"
            }
        }

    def claim_side(self, player: int) -> Optional[str]:
        if player == self.BLACK and self.black_token is None:
            self.black_token = str(uuid.uuid4())
            return self.black_token
        if player == self.WHITE and self.white_token is None:
            self.white_token = str(uuid.uuid4())
            return self.white_token
        return None

    def get_scores(self):
        black = sum(row.count(self.BLACK) for row in self.board)
        white = sum(row.count(self.WHITE) for row in self.board)
        return {"black": black, "white": white}

    def is_valid_coord(self, x, y):
        return 0 <= x < 8 and 0 <= y < 8

    def get_valid_moves(self, player: int) -> List[Tuple[int, int]]:
        moves = []
        for y in range(8):
            for x in range(8):
                if self.can_move(x, y, player):
                    moves.append((x, y))
        return moves

    def can_move(self, x: int, y: int, player: int) -> bool:
        if self.board[y][x] != self.EMPTY:
            return False
        
        opponent = self.WHITE if player == self.BLACK else self.BLACK
        
        # Directions: N, NE, E, SE, S, SW, W, NW
        directions = [
            (0, -1), (1, -1), (1, 0), (1, 1),
            (0, 1), (-1, 1), (-1, 0), (-1, -1)
        ]
        
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if self.is_valid_coord(nx, ny) and self.board[ny][nx] == opponent:
                # Keep going in this direction to see if we find our own piece
                nx += dx
                ny += dy
                while self.is_valid_coord(nx, ny):
                    if self.board[ny][nx] == self.EMPTY:
                        break
                    if self.board[ny][nx] == player:
                        return True
                    nx += dx
                    ny += dy
        return False

    def make_move(self, x: int, y: int, player: int, token: str) -> bool:
        # Check token
        if player == self.BLACK and token != self.black_token:
            return False
        if player == self.WHITE and token != self.white_token:
            return False
        
        if self.is_over or self.current_turn != player:
            return False
        
        # Check cooldown
        if time.time() - self.last_move_time < self.settings.turn_cooldown:
            return False

        if not self.can_move(x, y, player):
            return False

        # Execute move
        self.board[y][x] = player
        self.flip_pieces(x, y, player)
        
        self.last_move_time = time.time()
        self.history.append((x, y, player))
        
        # Switch turn
        self.next_turn()
        return True

    def flip_pieces(self, x: int, y: int, player: int):
        opponent = self.WHITE if player == self.BLACK else self.BLACK
        directions = [
            (0, -1), (1, -1), (1, 0), (1, 1),
            (0, 1), (-1, 1), (-1, 0), (-1, -1)
        ]
        
        for dx, dy in directions:
            to_flip = []
            nx, ny = x + dx, y + dy
            while self.is_valid_coord(nx, ny) and self.board[ny][nx] == opponent:
                to_flip.append((nx, ny))
                nx += dx
                ny += dy
            
            if self.is_valid_coord(nx, ny) and self.board[ny][nx] == player:
                for fx, fy in to_flip:
                    self.board[fy][fx] = player

    def next_turn(self):
        opponent = self.WHITE if self.current_turn == self.BLACK else self.BLACK
        
        if self.get_valid_moves(opponent):
            self.current_turn = opponent
        elif self.get_valid_moves(self.current_turn):
            # Opponent has no moves, current player keeps turn
            pass
        else:
            # No one has moves, game over
            self.end_game()

    def end_game(self):
        self.is_over = True
        scores = self.get_scores()
        if scores["black"] > scores["white"]:
            self.winner = self.BLACK
        elif scores["white"] > scores["black"]:
            self.winner = self.WHITE
        else:
            self.winner = 0  # Tie
