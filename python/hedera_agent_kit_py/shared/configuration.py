from enum import Enum
from typing import Optional, List

from .hedera_utils.mirrornode.hedera_mirrornode_service_interface import IHederaMirrornodeService
from .plugin import Plugin


class AgentMode(str, Enum):
    AUTONOMOUS = "autonomous"
    RETURN_BYTES = "returnBytes"


class Context:
    def __init__(
            self,
            account_id: Optional[str] = None,
            account_public_key: Optional[str] = None,
            mode: Optional[AgentMode] = None,
            mirrornode_service: Optional[IHederaMirrornodeService] = None,
    ):
        # Account is a Connected Account ID.
        self.account_id = account_id

        # Account Public Key is either passed in configuration or fetched based on the passed accountId
        self.account_public_key = account_public_key

        # defines if the agent executes the transactions or returns the raw transaction bytes
        self.mode = mode

        # Mirrornode config
        self.mirrornode_service = mirrornode_service


class Configuration:
    def __init__(
            self,
            tools: Optional[List[str]] = None,
            plugins: Optional[List[Plugin]] = None,
            context: Optional[Context] = None,
    ):
        self.tools = tools  # if empty, all tools will be used.
        self.plugins = plugins  # external plugins to load
        self.context = context
