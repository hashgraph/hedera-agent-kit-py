from hiero_sdk_python import Client, PublicKey

from hedera_agent_kit.shared.configuration import Context, AgentMode
from hedera_agent_kit.shared.hedera_utils.mirrornode import get_mirrornode_service
from hedera_agent_kit.shared.hedera_utils.mirrornode.hedera_mirrornode_service_interface import (
    IHederaMirrornodeService,
)
from hedera_agent_kit.shared.utils import ledger_id_from_network


class AccountResolver:
    """
    Utility class for resolving Hedera account information based on context and agent mode.
    """

    @staticmethod
    def get_default_account(context: Context, client: Client) -> str:
        """
        Gets the default account based on the agent mode and context.
        In RETURN_BYTES mode, prefers context.accountId (user's account).
        In AUTONOMOUS mode or when no context account, uses an operator account.
        """
        # Prefer context.account_id (user's account) if it is set
        if context.account_id:
            return context.account_id

        # Use operator account if context.account_id is not set
        operator_account = getattr(client, "operatorAccountId", None)
        if not operator_account:
            raise ValueError(
                "No account available: neither context.account_id nor operator account"
            )

        return str(operator_account)

    @staticmethod
    async def get_default_public_key(context: Context, client: Client) -> PublicKey:
        """
        Gets the default public key for the current context.
        In AUTONOMOUS mode, uses the client's operator key.
        Otherwise, fetches it from the mirrornode for the user's account.
        """
        if context.mode == AgentMode.AUTONOMOUS:
            return client.operator_private_key.public_key()

        default_account = AccountResolver.get_default_account(context, client)
        mirrornode_service = get_mirrornode_service(
            context.mirrornode_service, ledger_id_from_network(client.network)
        )

        default_account_details = await mirrornode_service.get_account(default_account)

        if not getattr(default_account_details, "accountPublicKey", None):
            raise ValueError("No public key available for the default account")

        return PublicKey.from_string(default_account_details["account_public_key"])

    @staticmethod
    def resolve_account(
        provided_account: str | None, context: Context, client: Client
    ) -> str:
        """
        Resolves an account ID, using the provided account or falling back to the default.
        """
        return provided_account or AccountResolver.get_default_account(context, client)

    @staticmethod
    def get_default_account_description(context: Context) -> str:
        """
        Gets a description of which account will be used as default for prompts.
        """
        if context.mode == AgentMode.RETURN_BYTES and context.account_id:
            return f"user account ({context.account_id})"
        return "operator account"

    @staticmethod
    def is_hedera_address(address: str) -> bool:
        """
        Checks if the given address is a Hedera address (starts with '0.' or '0.0.').
        """
        return address.startswith("0.") or address.startswith("0.0.")

    @staticmethod
    async def get_hedera_evm_address(
        address: str, mirror_node: IHederaMirrornodeService
    ) -> str:
        """
        Converts a Hedera address to its corresponding EVM address if applicable.
        """
        if not AccountResolver.is_hedera_address(address):
            return address

        account = await mirror_node.get_account(address)
        return account.get("evm_address")

    @staticmethod
    async def get_hedera_account_id(
        address: str, mirror_node: IHederaMirrornodeService
    ) -> str:
        """
        Converts an EVM address to its corresponding Hedera account ID if applicable.
        If already a Hedera address, returns it as-is.
        """
        if AccountResolver.is_hedera_address(address):
            return address

        account = await mirror_node.get_account(address)
        return account.get("account_id")
