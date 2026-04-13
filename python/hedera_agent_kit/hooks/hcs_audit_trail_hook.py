import json
from typing import Any, List, Optional

from hiero_sdk_python import (
    Client,
    TopicMessageSubmitTransaction,
    TopicId,
    ResponseCode,
)
from hiero_sdk_python.hapi.services.response_code_pb2 import ResponseCodeEnum

from hedera_agent_kit.shared.hook import (
    AbstractHook,
    PostSecondaryActionParams,
    PreToolExecutionParams,
)
from .utils import stringify_recursive
from hedera_agent_kit.shared.configuration import AgentMode, Context
from hedera_agent_kit.shared.models import RawTransactionResponse


class HcsAuditTrailHook(AbstractHook):
    """
    Hook to add an audit trail of tool executions to a Hedera Consensus Service (HCS) topic.

    This hook logs information about tool executions, including parameters and transaction
    results, to a specified HCS topic. It is only available in AUTONOMOUS mode.
    It does not log the data returned by the query actions - just the fact that the query action was executed and with what params.

    @warning If a paid topic (HIP-991: https://hips.hedera.com/hip/hip-991) is provided,
    it could potentially drain the provided logging client's funds due to message submission fees.
    """

    def __init__(
        self,
        relevant_tools: List[str],
        hcs_topic_id: str,
        logging_client: Optional[Client] = None,
    ):
        """
        Initializes the HCS Audit Trail Hook.

        Args:
            relevant_tools (List[str]): List of tool names that this hook should monitor.
            hcs_topic_id (str): The Hedera Council ID for the HCS topic where logs will be sent.
            logging_client (Optional[Client]): An optional Hedera client specifically for logging.
                If not provided, the client from the tool execution will be used.
        """
        self._relevant_tools = relevant_tools
        self.hcs_topic_id = hcs_topic_id
        self.logging_client = logging_client
        self._name = "HCS Audit Trail Hook"
        self._description = "Hook to add audit trail to HCS messages. Available only in Agent Mode AUTONOMOUS."

    @property
    def name(self) -> str:
        """The name of the hook."""
        return self._name

    @property
    def description(self) -> str:
        """A brief description of the hook's purpose."""
        return self._description

    @property
    def relevant_tools(self) -> List[str]:
        """A list of tools that this hook is applied to."""
        return self._relevant_tools

    async def pre_tool_execution_hook(
        self, context: Context, params: PreToolExecutionParams, method: str
    ) -> Any:
        """
        Validates the execution mode before a tool is executed.

        Args:
            context (Context): The agent's runtime context.
            params (PreToolExecutionParams): The parameters provided to the tool.
            method (str): The name of the tool method being executed.

        Raises:
            RuntimeError: If the agent is not in AUTONOMOUS mode for a monitored tool.
        """
        if method not in self.relevant_tools:
            return

        # HcsAuditTrailHook is available only in Agent Mode AUTONOMOUS.
        if context.mode == AgentMode.RETURN_BYTES:
            print(
                f"Unsupported hook: HcsAuditTrailHook is available only in Agent Mode AUTONOMOUS. Stopping the agent execution before tool {method} is executed."
            )
            raise RuntimeError(
                f"Unsupported hook: HcsAuditTrailHook is available only in Agent Mode AUTONOMOUS. Stopping the agent execution before tool {method} is executed."
            )

    async def post_secondary_action_hook(
        self, _context: Context, params: PostSecondaryActionParams, method: str
    ) -> Any:
        """
        Captures tool execution results and submits an audit message to HCS.

        Args:
            _context (Context): The agent's runtime context.
            params (PostSecondaryActionParams): Results and metadata from the tool execution.
            method (str): The name of the tool method that was executed.
        """
        if method not in self.relevant_tools:
            return

        target_client = self.logging_client

        # HcsAuditTrailHook will use the agent's operator account client if no logging specific client is provided on hook initialization.
        if not target_client:
            print(
                "HcsAuditTrailHook: No logging specific client provided. Using the agent's operator account client."
            )
            target_client = params.client

        raw_res = params.tool_result.raw if hasattr(params.tool_result, "raw") else None

        transaction_id = "N/A (query action)"
        status = "N/A (query action)"
        token_id = "N/A"
        topic_id = "N/A"
        schedule_id = "N/A"
        account_id = "N/A"

        if isinstance(raw_res, RawTransactionResponse):
            transaction_id = (
                str(raw_res.transaction_id)
                if raw_res.transaction_id
                else transaction_id
            )
            status = raw_res.status or status
            token_id = str(raw_res.token_id) if raw_res.token_id else token_id
            topic_id = str(raw_res.topic_id) if raw_res.topic_id else topic_id
            schedule_id = (
                str(raw_res.schedule_id) if raw_res.schedule_id else schedule_id
            )
            account_id = str(raw_res.account_id) if raw_res.account_id else account_id

        # Create a clean copy for logging to avoid mutating the original
        loggable_params = stringify_recursive(params.normalized_params)

        log_message = (
            f"Agent executed tool {method} with params {json.dumps(loggable_params, indent=2)}.\n"
            f"Transaction ID: {transaction_id}\n"
            f"Transaction Status: {status}\n"
            f"Token ID: {token_id}\n"
            f"Topic ID: {topic_id}\n"
            f"Schedule ID: {schedule_id}\n"
            f"Account ID: {account_id}\n"
        )
        await self.post_message_to_hcs_topic(log_message, target_client)

    async def post_message_to_hcs_topic(self, message: str, client: Client):
        """
        Submits a message to the HCS topic.

        Args:
            message (str): The message content to submit.
            client (Client): The Hedera client to use for the submission.
        """
        topic_id_str = self.hcs_topic_id
        if not topic_id_str:
            return

        try:
            from hiero_sdk_python import TransactionReceipt

            tx = TopicMessageSubmitTransaction()
            tx.set_topic_id(TopicId.from_string(topic_id_str))
            tx.set_message(message)

            receipt: TransactionReceipt = tx.execute(client)

            if receipt.status != ResponseCodeEnum.SUCCESS:
                print(
                    f"HcsAuditTrailHook: Failed to submit message to HCS topic {topic_id_str}: {ResponseCode(receipt.status).name}"
                )
        except Exception as e:
            print(
                f"HcsAuditTrailHook: Error submitting message to HCS topic {topic_id_str}: {str(e)}"
            )
