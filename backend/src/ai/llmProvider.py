from typing import Protocol, runtime_checkable


@runtime_checkable
class LlmTransport(Protocol):
    async def chat(self, *, system: str, user: str, timeout_seconds: float) -> str:
        """Return assistant text only."""
