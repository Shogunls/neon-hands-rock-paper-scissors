import unittest

from game_logic import score_round


class GameLogicTests(unittest.TestCase):
    def test_all_nine_outcomes(self):
        expected = {
            ("rock", "rock"): "draw",
            ("rock", "paper"): "lose",
            ("rock", "scissors"): "win",
            ("paper", "rock"): "win",
            ("paper", "paper"): "draw",
            ("paper", "scissors"): "lose",
            ("scissors", "rock"): "lose",
            ("scissors", "paper"): "win",
            ("scissors", "scissors"): "draw",
        }
        for moves, outcome in expected.items():
            with self.subTest(moves=moves):
                self.assertEqual(score_round(*moves), outcome)

    def test_rejects_unknown_move(self):
        with self.assertRaises(ValueError):
            score_round("cheat", "rock")


if __name__ == "__main__":
    unittest.main()
