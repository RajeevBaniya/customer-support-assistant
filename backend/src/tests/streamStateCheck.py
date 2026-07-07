import json

from src.realtime.stream_state import format_sse_event


def test_format_sse_event_wraps_json_payload() -> None:
    line = format_sse_event({"type": "token", "data": {"text": "a"}})
    assert line.startswith("data: ")
    assert line.endswith("\n\n")
    payload = json.loads(line.removeprefix("data: ").strip())
    assert payload == {"type": "token", "data": {"text": "a"}}
