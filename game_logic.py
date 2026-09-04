"""Pure, testable Rock Paper Scissors rules."""

CHOICES = ("rock", "paper", "scissors")
_WINNING_PAIRS = frozenset(
    {
        ("rock", "scissors"),
        ("paper", "rock"),
        ("scissors", "paper"),
    }
)


def score_round(player, computer):
    """Return ``win``, ``lose`` or ``draw`` for two validated moves."""
    if player not in CHOICES or computer not in CHOICES:
        raise ValueError("Move must be rock, paper, or scissors.")
    if player == computer:
        return "draw"
    return "win" if (player, computer) in _WINNING_PAIRS else "lose"
