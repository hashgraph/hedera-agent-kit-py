"""Plugin registration and discovery utilities for the Hedera Agent Kit.

This module defines a simple registry to collect and expose tool providers
(plugins). It can load predefined core plugins or user-registered plugins and
return a flat list of `Tool` instances given a `Context`.
"""
from __future__ import annotations

from typing import List, Dict

from hedera_agent_kit_py.shared.tool import Tool
from .configuration import Context
from .plugin import Plugin
from ..plugins.core_account_plugin import core_account_plugin

CORE_PLUGINS: List[Plugin] = [
    core_account_plugin
    # TODO: Add more core plugins here
]


class PluginRegistry:
    """A registry for collecting and exposing Hedera Agent Kit plugins.

    The registry can provide tools from pre-defined core plugins or from plugins
    registered at runtime by consumers.
    """

    def __init__(self):
        """Initialize an empty registry."""
        self.plugins: Dict[str, Plugin] = {}

    def register(self, plugin: Plugin) -> None:
        """Register a plugin, overwriting any existing plugin with the same name.

        Args:
            plugin: The plugin to add to the registry.
        """
        if plugin.name in self.plugins:
            print(
                f'Warning: Plugin "{plugin.name}" is already registered. Overwriting.'
            )
        self.plugins[plugin.name] = plugin

    def get_plugins(self) -> List[Plugin]:
        """Return the list of registered plugins."""
        return list(self.plugins.values())

    def _load_core_plugins(self, context: Context) -> List[Tool]:
        """Load tools from built-in core plugins.

        Args:
            context: The runtime context passed to plugin `tools()` factories.

        Returns:
            A flat list of tool instances from all core plugins.
        """
        plugin_tools: List[Tool] = []
        for plugin in CORE_PLUGINS:
            try:
                tools: list[Tool] = plugin.tools(context)
                plugin_tools.extend(tools)
            except Exception as error:
                print(f'Error loading tools from core plugin "{plugin.name}": {error}')
        return plugin_tools

    def _load_plugins(self, context: Context) -> List[Tool]:
        """Load tools from all user-registered plugins.

        Args:
            context: The runtime context passed to plugin `tools()` factories.

        Returns:
            A flat list of tool instances from all registered plugins.
        """
        plugin_tools: List[Tool] = []
        for plugin in self.plugins.values():
            try:
                tools: list[Tool] = plugin.tools(context)
                plugin_tools.extend(tools)
            except Exception as error:
                print(f'Error loading tools from plugin "{plugin.name}": {error}')
        return plugin_tools

    def get_tools(self, context: Context) -> List[Tool]:
        """Return tools from core plugins if none registered, else from registry.

        Args:
            context: The runtime context used when instantiating tools.
        """
        if not self.plugins:
            return self._load_core_plugins(context)
        else:
            return self._load_plugins(context)

    def clear(self) -> None:
        """Remove all registered plugins from the registry."""
        self.plugins.clear()
