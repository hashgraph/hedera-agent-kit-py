from .account_resolver import AccountResolver
from ..configuration import AgentMode, Context


class PromptGenerator:
    """
    Utility class for generating consistent prompt snippets and parameter descriptions
    for tools and user interactions.
    """

    @staticmethod
    def get_context_snippet(context: Context) -> str:
        """
        Generates a consistent context snippet for tool prompts.
        """
        lines = ["Context:"]

        if context.mode == AgentMode.RETURN_BYTES:
            lines.append(
                "- Mode: Return Bytes (preparing transactions for user signing)"
            )
            if context.account_id:
                lines.append(
                    f"- User Account: {context.account_id} (default for transaction parameters)"
                )
                lines.append(
                    f"- When no account is specified, {context.account_id} will be used"
                )
            else:
                lines.append("- User Account: Not specified")
                lines.append(
                    "- When no account is specified, the operator account will be used"
                )
        elif context.mode == AgentMode.AUTONOMOUS:
            lines.append("- Mode: Autonomous (agent executes transactions directly)")
            if context.account_id:
                lines.append(f"- User Account: {context.account_id}")
            lines.append(
                "- When no account is specified, the operator account will be used"
            )
        else:
            lines.append(f"- Mode: {context.mode or 'Not specified'}")
            if context.account_id:
                lines.append(f"- User Account: {context.account_id}")
            lines.append("- Default account will be determined at execution time")

        return "\n".join(lines)

    @staticmethod
    def get_any_address_parameter_description(
        param_name: str, context: Context, is_required: bool = False
    ) -> str:
        """
        Generates a description for any account/EVM address parameter.
        """
        if is_required:
            return f"{param_name} (str, required): The account address. This can be the EVM address or the Hedera account id"

        default_desc = AccountResolver.get_default_account_description(context)
        return f"{param_name} (str, optional): The Hedera account ID or EVM address. If not provided, defaults to the {default_desc}"

    @staticmethod
    def get_account_parameter_description(
        param_name: str, context: Context, is_required: bool = False
    ) -> str:
        """
        Generates a consistent description for optional account parameters.
        """
        if is_required:
            return f"{param_name} (str, required): The Hedera account ID"

        default_desc = AccountResolver.get_default_account_description(context)
        return f"{param_name} (str, optional): The Hedera account ID. If not provided, defaults to the {default_desc}"

    @staticmethod
    def get_parameter_usage_instructions() -> str:
        """
        Generates consistent parameter usage instructions.
        """
        return """
Important:
- Only include optional parameters if explicitly provided by the user
- Do not generate placeholder values for optional fields
- Leave optional parameters undefined if not specified by the user
- Important: If the user mentions multiple recipients or amounts and tool accepts an array, combine all recipients, tokens or similar assets into a single array and make exactly one call to that tool. Do not split the action into multiple tool calls if it's possible to do so.
"""

    @staticmethod
    def get_scheduled_transaction_params_description(context: Context) -> str:
        """
        Generates parameter descriptions for scheduled transactions.
        """
        default_account_desc = AccountResolver.get_default_account_description(context)
        return f"""schedulingParams (object, optional): Parameters for scheduling this transaction instead of executing immediately.

**Fields that apply to the *schedule entity*, not the inner transaction:**

- **isScheduled** (boolean, optional, default false):  
  If true, the transaction will be created as a scheduled transaction.  
  If false or omitted, all other scheduling parameters will be ignored.
  *Always set to true when user asks for scheduling a transaction.*

- **adminKey** (boolean|string, optional, default false):  
  Admin key that can delete or modify the scheduled transaction before execution.  
  - If true, the operator key will be used.  
  - If false or omitted, no admin key is set.  
  - If a string is passed, it will be used as the admin key.

- **payerAccountId** (string, optional):  
  Account that will pay the transaction fee when the scheduled transaction executes.  
  Defaults to the {default_account_desc}.

- **expirationTime** (string, optional, ISO 8601):  
  Time when the scheduled transaction will expire if not fully signed.

- **waitForExpiry** (boolean, optional, default false):  
  If true, the scheduled transaction will be executed at its expiration time, regardless of when all required signatures are collected.  
  If false, the transaction will execute as soon as all required signatures are present.

**Notes**
- Setting any scheduling parameter implies delayed execution through the Hedera schedule service.
- The network executes the scheduled transaction automatically once all required signatures are collected.
"""
