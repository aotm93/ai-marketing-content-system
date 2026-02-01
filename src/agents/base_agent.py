from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
from src.core.ai_provider import AIProviderInterface
from src.core.event_bus import EventBus, Event

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all AI agents"""

    def __init__(
        self,
        name: str = "base_agent",
        ai_provider: Optional[AIProviderInterface] = None,
        event_bus: Optional[EventBus] = None
    ):
        self.name = name
        self.ai_provider = ai_provider
        self.event_bus = event_bus
        logger.info(f"Initialized agent: {name}")

    @abstractmethod
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's main task"""
        pass

    async def publish_event(self, event_name: str, data: Dict[str, Any]) -> None:
        """Publish an event to the event bus"""
        if self.event_bus is None:
            logger.debug(f"{self.name} skipping event publish (no event_bus): {event_name}")
            return

        event = Event(name=event_name, data=data, source=self.name)
        await self.event_bus.publish(event)
        logger.info(f"{self.name} published event: {event_name}")

    async def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text using AI provider"""
        return await self.ai_provider.generate_text(prompt, **kwargs)
