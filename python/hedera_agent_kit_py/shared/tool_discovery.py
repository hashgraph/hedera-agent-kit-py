from __future__ import annotations

from typing import Optional, Any

from .configuration import Context, Configuration
from .plugin import Plugin
from .plugin_registry import PluginRegistry
from .tool import Tool


class ToolDiscovery:
    def __init__(self, plugins: Optional[list[Plugin]] = None):
        self.plugin_registry = PluginRegistry()
        if plugins:
            for plugin in plugins:
                self.plugin_registry.register(plugin)

    def get_all_tools(
        self, context: Context, configuration: Optional[Configuration] = None
    ) -> list[Tool]:
        # Get plugin tools
        plugin_tools: list[Tool] = self.plugin_registry.get_tools(context)

        # Merge all tools (core tools take precedence in case of name conflicts)
        all_tools: list[Any] = []
        all_tool_names: set[str] = set()

        for plugin_tool in plugin_tools:
            if plugin_tool.method not in all_tool_names:
                all_tools.append(plugin_tool)
                all_tool_names.add(plugin_tool.method)
            else:
                print(
                    f'Warning: Plugin tool "{plugin_tool.method}" conflicts with core tool. Using core tool.'
                )

        # Apply tool filtering if specified in the configuration
        if configuration and configuration.tools and len(configuration.tools) > 0:
            return [tool for tool in all_tools if tool.method in configuration.tools]

        return all_tools

    @staticmethod
    def create_from_configuration(configuration: Configuration) -> ToolDiscovery:
        return ToolDiscovery(configuration.plugins or [])
