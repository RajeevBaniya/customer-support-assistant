from pathlib import Path

_PROMPTS = Path(__file__).resolve().parent / "prompts"


def _read_prompt(name: str) -> str:
    return (_PROMPTS / name).read_text(encoding="utf-8").strip()


def load_insufficient_context_answer() -> str:
    return _read_prompt("insufficient_context.txt")


def build_prompt_pair(
    *,
    user_query: str,
    context_text: str,
    prior_turns_text: str | None = None,
) -> tuple[str, str]:
    system = _read_prompt("system_grounding.txt")
    memory_block = ""
    block = (prior_turns_text or "").strip()
    if block:
        memory_block = _read_prompt("chat_memory_turns.txt").format(turns=block).rstrip() + "\n\n"
    user = _read_prompt("user_task.txt").format(
        memory_block=memory_block,
        context=context_text,
        query=user_query,
    )
    return system, user
