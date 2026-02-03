import unittest
import sys
import os
import time

# Add the current directory to sys.path so we can import backend
sys.path.append(os.getcwd())

from backend.game import ReversiGame, GameSettings

class TestReversiGame(unittest.TestCase):
    def test_initial_board(self):
        game = ReversiGame()
        self.assertEqual(game.board[3][3], game.WHITE)
        self.assertEqual(game.board[3][4], game.BLACK)
        self.assertEqual(game.board[4][3], game.BLACK)
        self.assertEqual(game.board[4][4], game.WHITE)
        self.assertEqual(game.current_turn, game.BLACK)

    def test_valid_moves_initial(self):
        game = ReversiGame()
        moves = game.get_valid_moves(game.BLACK)
        expected = [(3, 2), (2, 3), (5, 4), (4, 5)]
        self.assertEqual(set(moves), set(expected))

    def test_make_move(self):
        game = ReversiGame()
        # Black moves to (3, 2)
        success = game.make_move(3, 2, game.BLACK, game.black_token)
        self.assertTrue(success)
        self.assertEqual(game.board[2][3], game.BLACK)
        self.assertEqual(game.board[3][3], game.BLACK) # Flipped
        self.assertEqual(game.current_turn, game.WHITE)

    def test_invalid_token(self):
        game = ReversiGame()
        success = game.make_move(3, 2, game.BLACK, "wrong-token")
        self.assertFalse(success)

    def test_wrong_turn(self):
        game = ReversiGame()
        success = game.make_move(2, 4, game.WHITE, game.white_token)
        self.assertFalse(success)

    def test_turn_cooldown(self):
        settings = GameSettings(turn_cooldown=0.5)
        game = ReversiGame(settings)
        game.make_move(3, 2, game.BLACK, game.black_token)
        # Immediate move by White should fail
        success = game.make_move(2, 2, game.WHITE, game.white_token)
        self.assertFalse(success)
        # Wait and try again
        time.sleep(0.6)
        success = game.make_move(2, 2, game.WHITE, game.white_token)
        self.assertTrue(success)

if __name__ == "__main__":
    unittest.main()
