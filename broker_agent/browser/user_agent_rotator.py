import asyncio
import itertools


class UserAgentRotator:
    """Cycles through a list of user agents."""

    def __init__(self, user_agents: list[str]):
        if not user_agents:
            raise ValueError("User agent list cannot be empty.")
        self._user_agents = user_agents
        self._iterator = itertools.cycle(self._user_agents)
        self._lock = asyncio.Lock()  # Ensure thread-safe access in async context

    async def get_next_agent(self) -> str:
        """Returns the next user agent in a thread-safe manner."""
        async with self._lock:
            return next(self._iterator)
