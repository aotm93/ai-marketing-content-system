from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class PluginInterface(ABC):
    """Base interface for all plugins"""

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the plugin with configuration"""
        pass

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the plugin's main functionality"""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup resources"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name"""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version"""
        pass


class PluginManager:
    """Manages plugin lifecycle and execution"""

    def __init__(self):
        self._plugins: Dict[str, PluginInterface] = {}
        self._plugin_configs: Dict[str, Dict[str, Any]] = {}
        logger.info("PluginManager initialized")

    def register_plugin(self, plugin: PluginInterface, config: Dict[str, Any] = None) -> None:
        """Register a plugin"""
        plugin_name = plugin.name
        if plugin_name in self._plugins:
            logger.warning(f"Plugin {plugin_name} already registered, replacing")

        self._plugins[plugin_name] = plugin
        self._plugin_configs[plugin_name] = config or {}
        plugin.initialize(self._plugin_configs[plugin_name])
        logger.info(f"Registered plugin: {plugin_name} v{plugin.version}")

    def unregister_plugin(self, plugin_name: str) -> None:
        """Unregister a plugin"""
        if plugin_name in self._plugins:
            self._plugins[plugin_name].cleanup()
            del self._plugins[plugin_name]
            del self._plugin_configs[plugin_name]
            logger.info(f"Unregistered plugin: {plugin_name}")

    async def execute_plugin(self, plugin_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific plugin"""
        if plugin_name not in self._plugins:
            raise ValueError(f"Plugin not found: {plugin_name}")

        logger.info(f"Executing plugin: {plugin_name}")
        return await self._plugins[plugin_name].execute(context)

    def get_plugin(self, plugin_name: str) -> Optional[PluginInterface]:
        """Get a plugin by name"""
        return self._plugins.get(plugin_name)

    def list_plugins(self) -> List[str]:
        """List all registered plugins"""
        return list(self._plugins.keys())

    def cleanup_all(self) -> None:
        """Cleanup all plugins"""
        for plugin in self._plugins.values():
            plugin.cleanup()
        logger.info("All plugins cleaned up")


# Global plugin manager instance
plugin_manager = PluginManager()
