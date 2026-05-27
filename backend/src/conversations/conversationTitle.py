def conversation_title_from_first_message(text: str) -> str:
    s = text.strip()
    if len(s) <= 80:
        return s
    return s[:79] + "…"
