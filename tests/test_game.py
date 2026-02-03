import pytest
from backend.game import ReversiGame, GameSettings

def test_initial_board():
    game = ReversiGame()
    assert game.board[3][3] == game.WHITE
    assert game.board[3][4] == game.BLACK
    assert game.board[4][3] == game.BLACK
    assert game.board[4][4] == game.WHITE
    assert game.current_turn == game.BLACK

def test_valid_moves_initial():
    game = ReversiGame()
    moves = game.get_valid_moves(game.BLACK)
    # Valid moves for Black at start: (3,2), (2,3), (5,4), (4,5)
    expected = [(3, 2), (2, 3), (5, 4), (4, 5)]
    assert set(moves) == set(expected)

def test_make_move():
    game = ReversiGame()
    # Black moves to (3, 2)
    success = game.make_move(3, 2, game.BLACK, game.black_token)
    assert success is True
    assert game.board[2][3] == game.BLACK # Flips (3,3) -> No, (3,3) is White. Wait (3,2) is (x=3, y=2)
    # Correct indexing: board[y][x]
    assert game.board[2][3] == game.BLACK
    assert game.board[3][3] == game.BLACK # Flipped
    assert game.current_turn == game.WHITE

def test_invalid_token():
    game = ReversiGame()
    success = game.make_move(3, 2, game.BLACK, "wrong-token")
    assert success is False

def test_wrong_turn():
    game = ReversiGame()
    success = game.make_move(2, 4, game.WHITE, game.white_token)
    assert success is False

def test_turn_cooldown():
    settings = GameSettings(turn_cooldown=1.0)
    game = ReversiGame(settings)
    game.make_move(3, 2, game.BLACK, game.black_token)
    # Immediate move by White should fail
    success = game.make_move(2, 2, game.WHITE, game.white_token)
    assert success is False
