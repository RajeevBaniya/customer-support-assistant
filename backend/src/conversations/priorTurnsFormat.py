from typing import NamedTuple


class TurnLine(NamedTuple):
    role: str
    content: str


def prior_turns_block(
    rows_newest_first: list[TurnLine],
    max_chars: int,
    max_tokens: int = 2000,
) -> str:
    import tiktoken

    enc = tiktoken.get_encoding("cl100k_base")

    rows = list(reversed(rows_newest_first))
    blocks = [f"{m.role}: {m.content}" for m in rows]
    joined = "\n\n".join(blocks)
    while blocks:
        token_count = len(enc.encode(joined))
        char_count = len(joined)
        if token_count <= max_tokens and char_count <= max_chars:
            break
        blocks.pop(0)
        joined = "\n\n".join(blocks)
    return joined
