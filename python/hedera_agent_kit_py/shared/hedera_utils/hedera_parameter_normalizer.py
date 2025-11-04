from decimal import Decimal
from typing import Optional, Union, cast, Any, Type

from hiero_sdk_python import AccountId, PublicKey, Timestamp, Client
from hiero_sdk_python.schedule.schedule_create_transaction import ScheduleCreateParams
from pydantic import BaseModel, ValidationError

from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils import to_tinybars
from hedera_agent_kit_py.shared.parameter_schemas import (
    TransferHbarParameters,
    TransferHbarParametersNormalised,
    SchedulingParams,
    CreateTopicParameters,
    CreateTopicParametersNormalised,
)
from hedera_agent_kit_py.shared.utils.account_resolver import AccountResolver


class HederaParameterNormaliser:
    """Utility class to normalise and validate Hedera transaction parameters.

    This class provides static methods for:
        - Validating and parsing parameters against Pydantic schemas.
        - Normalising HBAR transfer parameters to Python SDK format.
        - Resolving account IDs and public keys.
        - Converting scheduling parameters to ScheduleCreateParams.
    """

    @staticmethod
    def parse_params_with_schema(
            params: Any,
            schema: Type[BaseModel],
    ) -> BaseModel:
        """Validate and parse parameters using a Pydantic schema.

        Args:
            params: The raw input parameters to validate.
            schema: The Pydantic model to validate against.

        Returns:
            BaseModel: An instance of the validated Pydantic model.

        Raises:
            ValueError: If validation fails, with a formatted description of the issues.
        """
        try:
            return schema.model_validate(params)
        except ValidationError as e:
            issues: str = HederaParameterNormaliser.format_validation_errors(e)
            raise ValueError(f"Invalid parameters: {issues}") from e

    @staticmethod
    def format_validation_errors(error: ValidationError) -> str:
        """Format Pydantic validation errors into a single human-readable string.

        Args:
            error: The ValidationError instance from Pydantic.

        Returns:
            str: Formatted error message summarising all field errors.
        """
        return "; ".join(
            f'Field "{err["loc"][0]}" - {err["msg"]}' for err in error.errors()
        )

    @staticmethod
    async def normalise_transfer_hbar(
            params: TransferHbarParameters,
            context: Context,
            client: Client,
    ) -> TransferHbarParametersNormalised:
        """Normalise HBAR transfer parameters to a format compatible with Python SDK.

        This resolves source accounts, converts amounts to tinybars, and optionally
        handles scheduled transactions.

        Args:
            params: Raw HBAR transfer parameters.
            context: Application context for resolving accounts.
            client: Hedera Client instance used for account resolution.

        Returns:
            TransferHbarParametersNormalised: Normalised HBAR transfer parameters
            ready to be used in Hedera transactions.

        Raises:
            ValueError: If transfer amounts are invalid (<= 0).
        """
        parsed_params: TransferHbarParameters = cast(
            TransferHbarParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, TransferHbarParameters
            ),
        )

        # Resolve source account
        source_account_id: str = AccountResolver.resolve_account(
            parsed_params.source_account_id, context, client
        )

        # Convert transfers to dict[AccountId, int]
        hbar_transfers: dict["AccountId", int] = {}
        total_tinybars: int = 0

        for transfer in parsed_params.transfers:
            tinybars = to_tinybars(Decimal(transfer.amount))
            if tinybars <= 0:
                raise ValueError(f"Invalid transfer amount: {transfer.amount}")

            hbar_transfers[AccountId.from_string(transfer.account_id)] = tinybars
            total_tinybars += tinybars

        # Subtract total from the source account
        hbar_transfers[AccountId.from_string(source_account_id)] = -total_tinybars

        # Handle optional scheduling
        scheduling_params = None
        if getattr(parsed_params, "scheduling_params", None):
            scheduling_params = (
                await HederaParameterNormaliser.normalise_scheduled_transaction_params(
                    parsed_params.scheduling_params, context, client
                )
            )

        return TransferHbarParametersNormalised(
            hbar_transfers=hbar_transfers,
            scheduling_params=scheduling_params,
            transaction_memo=getattr(parsed_params, "transaction_memo", None),
        )

    @staticmethod
    async def normalise_scheduled_transaction_params(
            scheduling: SchedulingParams,
            context: Context,
            client: Client,
    ) -> ScheduleCreateParams:
        """Convert SchedulingParams to a ScheduleCreateParams instance compatible with Python SDK.

        Resolves keys, payer account ID, and expiration time.

        Args:
            scheduling: Raw scheduling parameters.
            context: Application context for key/account resolution.
            client: Hedera Client instance used for key resolution.

        Returns:
            ScheduleCreateParams: Normalised scheduling parameters for SDK transactions.
        """
        # Resolve default user key
        user_public_key: PublicKey = await AccountResolver.get_default_public_key(
            context, client
        )

        # Resolve admin key
        admin_key: Optional[PublicKey] = HederaParameterNormaliser.resolve_key(
            scheduling.admin_key, user_public_key
        )

        # Resolve payer account ID
        payer_account_id: Optional[AccountId] = (
            AccountId.from_string(scheduling.payer_account_id)
            if scheduling.payer_account_id
            else None
        )

        # Resolve expiration time
        expiration_time: Optional[Timestamp] = (
            Timestamp.from_date(scheduling.expiration_time)
            if scheduling.expiration_time
            else None
        )

        return ScheduleCreateParams(
            admin_key=admin_key,
            payer_account_id=payer_account_id,
            expiration_time=expiration_time,
            wait_for_expiry=scheduling.wait_for_expiry or False,
        )

    @staticmethod
    def resolve_key(
            raw_value: Union[str, bool, None],
            user_key: PublicKey,
    ) -> Optional[PublicKey]:
        """Resolve a raw key input to a PublicKey instance.

        Args:
            raw_value: Can be None, a string representation of a key, or a boolean.
            user_key: Default user key to return if raw_value is True.

        Returns:
            Optional[PublicKey]: Resolved PublicKey or None if not applicable.
        """
        if raw_value is None:
            return None
        if isinstance(raw_value, str):
            try:
                return PublicKey.from_string_ed25519(raw_value)
            except Exception:
                return PublicKey.from_string_ecdsa(raw_value)
        if raw_value:
            return user_key
        return None

    @staticmethod
    async def normalise_create_topic_params(
            params: CreateTopicParameters,
            context: Context,
            client: Client,
            mirror_node,
    ) -> CreateTopicParametersNormalised:
        """Normalise create topic parameters to a format compatible with Python SDK.

        Args:
            params: Raw create topic parameters.
            context: Application context for resolving accounts.
            client: Hedera Client instance used for account resolution.
            mirror_node: Mirror node service for retrieving account information.

        Returns:
            CreateTopicParametersNormalised: Normalised create topic parameters
            ready to be used in Hedera transactions.

        Raises:
            ValueError: If default account ID or public key cannot be determined.
        """
        parsed_params: CreateTopicParameters = cast(
            CreateTopicParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, CreateTopicParameters
            ),
        )

        default_account_id: Optional[str] = AccountResolver.get_default_account(
            context, client
        )
        if not default_account_id:
            raise ValueError("Could not determine default account ID")

        normalised = CreateTopicParametersNormalised(
            is_submit_key=parsed_params.is_submit_key,
            is_admin_key=parsed_params.is_admin_key,
            topic_memo=parsed_params.topic_memo,
            transaction_memo=parsed_params.transaction_memo,
            memo=parsed_params.topic_memo,
        )

        # Get a public key for submitted key if needed
        if parsed_params.is_submit_key:
            try:
                account_info = await mirror_node.get_account(default_account_id)
                public_key_str = account_info.account_public_key
            except Exception:
                public_key_str = (
                    client.operator_private_key.public_key().to_string_der()
                    if client.operator_private_key.public_key()
                    else None
                )

            if not public_key_str:
                raise ValueError("Could not determine public key for submit key")

            normalised.submit_key = PublicKey.from_string(public_key_str)

        # Get public key for admin key if needed
        if parsed_params.is_admin_key:
            try:
                account_info = await mirror_node.get_account(default_account_id)
                public_key_str = account_info.account_public_key
            except Exception:
                public_key_str = (
                    client.operator_private_key.public_key().to_string_der()
                    if client.operator_private_key.public_key()
                    else None
                )

            if not public_key_str:
                raise ValueError("Could not determine public key for admin key")

            normalised.admin_key = PublicKey.from_string(public_key_str)

        return normalised
