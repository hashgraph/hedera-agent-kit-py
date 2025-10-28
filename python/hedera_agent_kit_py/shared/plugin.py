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
