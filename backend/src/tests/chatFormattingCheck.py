from src.conversations.conversationTitle import conversation_title_from_first_message
from src.conversations.priorTurnsFormat import TurnLine, prior_turns_block


def test_conversation_title_short_unchanged() -> None:
    assert conversation_title_from_first_message("  hello  ") == "hello"


def test_conversation_title_truncates_with_ellipsis() -> None:
    raw = "x" * 100
    out = conversation_title_from_first_message(raw)
    assert len(out) == 80
    assert out.endswith("…")


def test_prior_turns_block_respects_char_cap() -> None:
    long = "y" * 5000
    rows = [
        TurnLine("assistant", "short"),
        TurnLine("user", long),
    ]
    text = prior_turns_block(rows, max_chars=120)
    assert len(text) <= 120
