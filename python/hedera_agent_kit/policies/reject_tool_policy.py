import logging

from hedera_agent_kit import Context
from hedera_agent_kit.hooks.abstract_hook import PreToolExecutionParams
from hedera_agent_kit.shared.policy import Policy

logger = logging.getLogger(__name__)


class RejectToolPolicy(Policy):
    """
    Rejects calls of predefined tools based on their method names. This policy can be used to prevent the execution of certain tools in specific contexts, enhancing security and control over tool usage.
    """

    def __init__(self, relevant_tools: list[str]):
        super().__init__()
        self._relevant_tools = relevant_tools

    @property
    def name(self) -> str:
        return "Reject Tool Policy"

    @property
    def relevant_tools(self) -> list[str]:
        return self._relevant_tools

    """
    Hooks are called only for the relevant tools, so we can be sure that if this method is called, the tool call should be rejected.
    """

    async def should_block_pre_tool_execution(
        self, context: Context, params: PreToolExecutionParams, method
    ) -> bool:
        logger.info(
            "RejectToolPolicy: %s tool call rejected - tool not allowed",
            method,
        )
        return True
