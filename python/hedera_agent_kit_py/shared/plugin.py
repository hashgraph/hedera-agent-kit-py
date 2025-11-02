from typing import Callable, List

from .configuration import Context
from .tool import Tool


class Plugin:
    """Represents a plugin that provides a set of tools for the agent.

    Each plugin has a name, optional version and description, and a callable
    that returns a list of `Tool` instances based on the given `Context`.
    """

    def __init__(
        self,
        name: str,
        tools: Callable[[Context], List[Tool]],
        version: str | None = None,
        description: str | None = None,
    ):
        """
        Initialize a Plugin instance.

        Args:
            name (str): The unique name of the plugin.
            tools (Callable[[Context], List[Tool]]): A function that takes a `Context`
                and returns a list of `Tool` instances provided by the plugin.
            version (Optional[str]): Optional version string of the plugin.
            description (Optional[str]): Optional human-readable description of the plugin.
        """
        self.name = name
        self.version = version
        self.description = description
        self.tools = tools
