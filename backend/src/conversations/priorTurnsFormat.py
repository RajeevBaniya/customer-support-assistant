from typing import NamedTuple


class TurnLine(NamedTuple):
    role: str
    content: str


def prior_turns_block(rows_newest_first: list[TurnLine], max_chars: int) -> str:
    rows = list(reversed(rows_newest_first))
    blocks = [f"{m.role}: {m.content}" for m in rows]
    joined = "\n\n".join(blocks)
    while blocks and len(joined) > max_chars:
        blocks.pop(0)
        joined = "\n\n".join(blocks)
    return joined
