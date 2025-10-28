from decimal import Decimal
from typing import Optional, Union, cast, Any, Type

from hiero_sdk_python import AccountId, PublicKey, Timestamp, Client
from hiero_sdk_python.schedule.schedule_create_transaction import ScheduleCreateParams
from pydantic import BaseModel, ValidationError

from hedera_agent_kit_py.shared.utils.account_resolver import AccountResolver
from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils import to_tinybars
from hedera_agent_kit_py.shared.parameter_schemas import (
    TransferHbarParameters,
    TransferHbarParametersNormalised,
    SchedulingParams,
)


class HederaParameterNormaliser:
    @staticmethod
    def parse_params_with_schema(
        params: Any,
        schema: Type[BaseModel],
    ) -> BaseModel:
        """
        Validate and parse parameters using a pydantic schema.
        Raises ValueError if validation fails.
        """
        try:
            return schema.model_validate(params)
        except ValidationError as e:
            issues = HederaParameterNormaliser.format_validation_errors(e)
            raise ValueError(f"Invalid parameters: {issues}") from e

    @staticmethod
    def format_validation_errors(error: ValidationError) -> str:
        return "; ".join(
            f'Field "{err["loc"][0]}" - {err["msg"]}' for err in error.errors()
        )

    @staticmethod
    async def normalise_transfer_hbar(
        params: TransferHbarParameters,
        context: Context,
        client: Client,
    ) -> TransferHbarParametersNormalised:
        parsed_params: TransferHbarParameters = cast(
            TransferHbarParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, TransferHbarParameters
            ),
        )

        # Resolve source account
        source_account_id = AccountResolver.resolve_account(
            parsed_params.source_account_id, context, client
        )

        # Convert transfers to dict[AccountId, int]
        hbar_transfers: dict["AccountId", int] = {}
        total_tinybars = 0

        for transfer in parsed_params.transfers:
            tinybars = to_tinybars(Decimal(transfer.amount))
            if tinybars <= 0:
                raise ValueError(f"Invalid transfer amount: {transfer.amount}")

            hbar_transfers[AccountId.from_string(transfer.account_id)] = tinybars
            total_tinybars += tinybars

        # Subtract total from the source account
        hbar_transfers[AccountId.from_string(source_account_id)] = -total_tinybars

        # Handle scheduling
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
        """
        Normalises SchedulingParams to ScheduleCreateParams compatible with Python SDK.
        Resolves keys and account IDs.
        """
        # Resolve default user key
        user_public_key: PublicKey = await AccountResolver.get_default_public_key(
            context, client
        )

        # Resolve admin key
        admin_key = HederaParameterNormaliser.resolve_key(
            scheduling.admin_key, user_public_key
        )

        # Resolve payer account ID
        payer_account_id = (
            AccountId.from_string(scheduling.payer_account_id)
            if scheduling.payer_account_id
            else None
        )

        # Resolve expiration time
        expiration_time = (
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
