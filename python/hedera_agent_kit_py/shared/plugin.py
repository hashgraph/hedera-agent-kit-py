from typing import Callable, List, Dict

from .configuration import Context
from .tool import Tool


class Plugin:
    def __init__(
        self,
        name: str,
        tools: Callable[[Context], List[Tool]],
        version: str | None = None,
        description: str | None = None,
    ):
        self.name = name
        self.version = version
        self.description = description
        self.tools = tools


CORE_PLUGINS: List[Plugin] = [
    # Add core plugins here
]


class PluginRegistry:
    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}

    def register(self, plugin: Plugin) -> None:
        if plugin.name in self.plugins:
            print(
                f'Warning: Plugin "{plugin.name}" is already registered. Overwriting.'
            )
        self.plugins[plugin.name] = plugin

    def get_plugins(self) -> List[Plugin]:
        return list(self.plugins.values())

    def _load_core_plugins(self, context: Context) -> List[Tool]:
        plugin_tools: List[Tool] = []
        for plugin in CORE_PLUGINS:
            try:
                tools = plugin.tools(context)
                plugin_tools.extend(tools)
            except Exception as error:
                print(f'Error loading tools from core plugin "{plugin.name}": {error}')
        return plugin_tools

    def _load_plugins(self, context: Context) -> List[Tool]:
        plugin_tools: List[Tool] = []
        for plugin in self.plugins.values():
            try:
                tools = plugin.tools(context)
                plugin_tools.extend(tools)
            except Exception as error:
                print(f'Error loading tools from plugin "{plugin.name}": {error}')
        return plugin_tools

    def get_tools(self, context: Context) -> List[Tool]:
        if not self.plugins:
            return self._load_core_plugins(context)
        else:
            return self._load_plugins(context)

    def clear(self) -> None:
        self.plugins.clear()
