from typing import Dict, List, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Event data structure"""
    name: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "system"


class EventBus:
    """Event bus for loose coupling between components"""

    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}
        self._event_history: List[Event] = []
        logger.info("EventBus initialized")

    def subscribe(self, event_name: str, callback: Callable) -> None:
        """Subscribe to an event"""
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        self._listeners[event_name].append(callback)
        logger.info(f"Subscribed to event: {event_name}")

    def unsubscribe(self, event_name: str, callback: Callable) -> None:
        """Unsubscribe from an event"""
        if event_name in self._listeners:
            self._listeners[event_name].remove(callback)
            logger.info(f"Unsubscribed from event: {event_name}")

    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribers"""
        logger.info(f"Publishing event: {event.name}")
        self._event_history.append(event)

        if event.name in self._listeners:
            tasks = []
            for callback in self._listeners[event.name]:
                if asyncio.iscoroutinefunction(callback):
                    tasks.append(callback(event))
                else:
                    callback(event)

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    def get_history(self, event_name: str = None, limit: int = 100) -> List[Event]:
        """Get event history"""
        if event_name:
            return [e for e in self._event_history if e.name == event_name][-limit:]
        return self._event_history[-limit:]


# Global event bus instance
event_bus = EventBus()
