"""Base agent interface and shared LLM client wiring."""

from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    name: str = "base"

    @abstractmethod
    def run(self, **kwargs: Any) -> dict[str, Any]:
        """Execute agent logic and return structured output."""
