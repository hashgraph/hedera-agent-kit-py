from datetime import datetime
from decimal import Decimal
from typing import Optional, Union, cast, Any, Type

from hiero_sdk_python.contract.contract_id import ContractId
from hiero_sdk_python import (
    AccountId,
    PublicKey,
    Timestamp,
    Client,
    Hbar,
    TopicId,
    TokenId,
)
from hiero_sdk_python.schedule.schedule_create_transaction import ScheduleCreateParams
from pydantic import BaseModel, ValidationError
from web3 import Web3

from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils import to_tinybars
from hedera_agent_kit_py.shared.hedera_utils.mirrornode.hedera_mirrornode_service_interface import (
    IHederaMirrornodeService,
)
from hedera_agent_kit_py.shared.parameter_schemas import (
    TransferHbarParameters,
    TransferHbarParametersNormalised,
    SchedulingParams,
    DeleteAccountParameters,
    DeleteAccountParametersNormalised,
    CreateAccountParameters,
    CreateAccountParametersNormalised,
    UpdateAccountParameters,
    UpdateAccountParametersNormalised,
    CreateTopicParameters,
    CreateTopicParametersNormalised,
    SubmitTopicMessageParameters,
    SubmitTopicMessageParametersNormalised,
    DeleteTopicParameters,
    DeleteTopicParametersNormalised,
    AccountBalanceQueryParameters,
    AccountBalanceQueryParametersNormalised,
    GetTopicInfoParameters,
    ExchangeRateQueryParameters,
    ContractExecuteTransactionParametersNormalised,
    CreateERC20Parameters,
    TransactionRecordQueryParameters,
    TransactionRecordQueryParametersNormalised,
    UpdateTopicParameters,
    UpdateTopicParametersNormalised,
)

from hedera_agent_kit_py.shared.parameter_schemas.account_schema import (
    AccountQueryParametersNormalised,
    TransferHbarWithAllowanceParametersNormalised,
    TransferHbarWithAllowanceParameters,
)
from hedera_agent_kit_py.shared.parameter_schemas.token_schema import (
    GetTokenInfoParameters,
    DissociateTokenParameters,
    DissociateTokenParametersNormalised,
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
    async def normalise_create_account(
        params: CreateAccountParameters,
        context: Context,
        client: Client,
        mirrornode_service: IHederaMirrornodeService,
    ) -> CreateAccountParametersNormalised:
        """Normalize account-creation input into types the Python SDK expects.

        Actions performed:
        - Validates and parses `params` against the Pydantic schema.
        - Converts `initial_balance` to an `Hbar` instance (in tinybars).
        - Truncates `account_memo` to 100 characters when present.
        - Resolves the account public key in priority order:
            1. `params.public_key`
            2. `client.operator_private_key` (if available)
            3. Mirror node lookup for the default account (via `mirrornode_service`)
        - Normalizes optional scheduling parameters when `is_scheduled` is True.

        Args:
            params: Raw account creation parameters.
            context: Application context used for resolving defaults.
            client: Hedera `Client` used to access operator key when present.
            mirrornode_service: Mirror node service used to fetch account data.

        Returns:
            CreateAccountParametersNormalised: Parameters converted to SDK-compatible types.

        Raises:
            ValueError: If no public key can be resolved from params, client operator key, or mirror node.
        """
        parsed_params: CreateAccountParameters = cast(
            CreateAccountParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, CreateAccountParameters
            ),
        )

        # cast input to tinybars and build an instance of Hbar class
        initial_balance = Hbar(
            to_tinybars(Decimal(parsed_params.initial_balance)), in_tinybars=True
        )

        # truncate memo if longer than 100 chars
        account_memo: Optional[str] = parsed_params.account_memo
        if account_memo and len(account_memo) > 100:
            account_memo = account_memo[:100]

        # Try resolving the public_key in priority order
        public_key = parsed_params.public_key or (
            client.operator_private_key.public_key().to_string_der()
            if client.operator_private_key
            else None
        )

        if not public_key:
            default_account_id = AccountResolver.get_default_account(context, client)
            if default_account_id:
                account = await mirrornode_service.get_account(default_account_id)
                public_key = account.get("account_public_key")

        if not public_key:
            raise ValueError(
                "Unable to resolve public key: no param, mirror node, or client operator key available."
            )

        # Normalize scheduling parameters (if present and is_scheduled = True)
        scheduling_params: ScheduleCreateParams | None = None
        if getattr(parsed_params, "scheduling_params", None):
            if parsed_params.scheduling_params.is_scheduled:
                scheduling_params = await HederaParameterNormaliser.normalise_scheduled_transaction_params(
                    parsed_params.scheduling_params, context, client
                )

        return CreateAccountParametersNormalised(
            memo=account_memo,
            initial_balance=initial_balance,
            key=PublicKey.from_string(public_key),
            scheduling_params=scheduling_params,
            max_automatic_token_associations=parsed_params.max_automatic_token_associations,
        )

    @staticmethod
    def normalise_get_hbar_balance(
        params: AccountBalanceQueryParameters,
        context: Context,
        client: Client,
    ) -> AccountBalanceQueryParametersNormalised:
        """Normalise HBAR balance query parameters

        If an account_id is provided, it is used directly.
        Otherwise, the default account from AccountResolver is used.
        """

        parsed_params: AccountBalanceQueryParameters = cast(
            AccountBalanceQueryParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, AccountBalanceQueryParameters
            ),
        )

        if parsed_params.account_id is None:
            # Only resolve when no account ID is provided
            resolved_account_id = AccountResolver.get_default_account(context, client)
        else:
            resolved_account_id = parsed_params.account_id

        return AccountBalanceQueryParametersNormalised(account_id=resolved_account_id)

    @classmethod
    def normalise_get_account_query(cls, params) -> AccountQueryParametersNormalised:
        """Parse and validate account query parameters"""
        parsed_params: AccountQueryParametersNormalised = cast(
            AccountQueryParametersNormalised,
            HederaParameterNormaliser.parse_params_with_schema(
                params, AccountQueryParametersNormalised
            ),
        )
        return parsed_params

    @staticmethod
    async def normalise_create_topic_params(
        params: CreateTopicParameters,
        context: Context,
        client: Client,
    ) -> CreateTopicParametersNormalised:
        """Normalise 'create topic' parameters into a format compatible with the Python SDK.

        This function:
          - Validates and parses the raw parameters using the CreateTopicParameters schema.
          - Resolves the default account ID from context or client configuration.
          - Optionally resolves a submit key if `is_submit_key` is True.
          - Populates topic and transaction memos for SDK use.

        Args:
            params: Raw topic creation parameters provided by the user.
            context: Application context (contains environment configuration).
            client: Hedera Client instance used for resolving account and operator info.

        Returns:
            CreateTopicParametersNormalised: A validated, SDK-ready parameter object
            containing resolved submit key and memos.

        Raises:
            ValueError: If a default account ID cannot be determined.
        """
        # Validate and parse parameters
        parsed_params: CreateTopicParameters = cast(
            CreateTopicParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, CreateTopicParameters
            ),
        )

        # Resolve default account ID
        default_account_id: Optional[str] = AccountResolver.get_default_account(
            context, client
        )
        if not default_account_id:
            raise ValueError("Could not determine default account ID")

        account_public_key: PublicKey = await AccountResolver.get_default_public_key(
            context, client
        )

        # Build normalized parameter object
        normalised = CreateTopicParametersNormalised(
            memo=parsed_params.topic_memo,
            transaction_memo=parsed_params.transaction_memo,
            submit_key=None,
            admin_key=account_public_key,
        )

        # Optionally resolve submit key if requested
        if parsed_params.is_submit_key:
            normalised.submit_key = account_public_key

        return normalised

    @staticmethod
    async def normalise_create_erc20_params(
        params: CreateERC20Parameters,
        factory_address: str,
        ERC20_FACTORY_ABI: list[str],
        factory_contract_function_name: str,
        context: Context,
        client: Client,
    ) -> ContractExecuteTransactionParametersNormalised:
        """Normalise ERC20 creation parameters for BaseERC20Factory contract deployment.

        This method mirrors the TypeScript `normaliseCreateERC20Params` logic and prepares
        the encoded contract function call along with optional scheduling information.

        Args:
            params: Raw ERC20 creation parameters.
            factory_address: The address/ID of the ERC20 factory contract.
            ERC20_FACTORY_ABI: ABI of the BaseERC20Factory contract.
            factory_contract_function_name: Function to invoke (e.g., 'deployToken').
            context: Application context.
            client: Active Hedera client instance.

        Returns:
            ContractExecuteTransactionParametersNormalised: Normalised parameters ready for execution.
        """
        # Validate and parse parameters
        parsed_params: CreateERC20Parameters = cast(
            CreateERC20Parameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, CreateERC20Parameters
            ),
        )

        w3 = Web3()
        contract = w3.eth.contract(abi=ERC20_FACTORY_ABI)
        encoded_data = contract.encode_abi(
            abi_element_identifier=factory_contract_function_name,
            args=[
                parsed_params.token_name,
                parsed_params.token_symbol,
                parsed_params.decimals,
                parsed_params.initial_supply,
            ],
        )
        function_parameters = bytes.fromhex(encoded_data[2:])

        # Normalize scheduling parameters (if present and is_scheduled = True)
        scheduling_params: ScheduleCreateParams | None = None
        if getattr(parsed_params, "scheduling_params", None):
            if parsed_params.scheduling_params.is_scheduled:
                scheduling_params = await HederaParameterNormaliser.normalise_scheduled_transaction_params(
                    parsed_params.scheduling_params, context, client
                )

        return ContractExecuteTransactionParametersNormalised(
            contract_id=ContractId.from_string(factory_address),
            function_parameters=function_parameters,
            gas=3_000_000,  # TODO: make configurable
            scheduling_params=scheduling_params,
        )

    @staticmethod
    def normalise_get_topic_info(
        params: GetTopicInfoParameters,
    ):
        """
        Normalizes the input parameters for the 'get_topic_info' operation to ensure
        they adhere to the expected schema format. This function parses the input
        parameters utilizing a schema and type casts the result to the appropriate
        data type.

        :param params: The parameters for the 'get_topic_info' operation. These
            parameters should be of type 'GetTopicInfoParameters'.
        :type params: GetTopicInfoParameters

        :return: Parsed and normalized parameters after being verified against
            the schema.
        :rtype: GetTopicInfoParameters
        """
        parsed_params: GetTopicInfoParameters = cast(
            GetTopicInfoParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, GetTopicInfoParameters
            ),
        )

        return parsed_params

    @staticmethod
    def normalise_get_exchange_rate(
        params: ExchangeRateQueryParameters,
    ) -> ExchangeRateQueryParameters:
        """
        Normalises and parses the given exchange rate query parameters using a predefined
        schema. This method ensures that the input parameters adhere to the required structure
        and format specified by the schema.

        :param params: The exchange rate query parameters to be normalised. The parameter
            must conform to the type `ExchangeRateQueryParameters`.
        :type params: ExchangeRateQueryParameters

        :return: A parsed and normalised instance of `ExchangeRateQueryParameters`.
        :rtype: ExchangeRateQueryParameters
        """
        parsed_params: ExchangeRateQueryParameters = cast(
            ExchangeRateQueryParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, ExchangeRateQueryParameters
            ),
        )

        return parsed_params

    @staticmethod
    def normalise_delete_account(
        params: DeleteAccountParameters,
        context: Context,
        client: Client,
    ) -> DeleteAccountParametersNormalised:
        """Normalise delete account parameters to a format compatible with Python SDK.

        Args:
            params: Raw delete account parameters.
            context: Application context for resolving accounts.
            client: Hedera Client instance used for account resolution.

        Returns:
            DeleteAccountParametersNormalised: Normalised delete account parameters
            ready to be used in Hedera transactions.

        Raises:
            ValueError: If account ID is invalid or transfer account ID cannot be determined.
        """
        parsed_params: DeleteAccountParameters = cast(
            DeleteAccountParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, DeleteAccountParameters
            ),
        )

        if not AccountResolver.is_hedera_address(parsed_params.account_id):
            raise ValueError("Account ID must be a Hedera address")

        # If no transfer account ID is provided, use the operator account ID
        transfer_account_id: Optional[str] = (
            parsed_params.transfer_account_id
            if parsed_params.transfer_account_id
            else AccountResolver.get_default_account(context, client)
        )

        if not transfer_account_id:
            raise ValueError("Could not determine transfer account ID")

        return DeleteAccountParametersNormalised(
            account_id=AccountId.from_string(parsed_params.account_id),
            transfer_account_id=AccountId.from_string(transfer_account_id),
        )

    @staticmethod
    async def normalise_update_account(
        params: UpdateAccountParameters,
        context: Context,
        client: Client,
    ) -> UpdateAccountParametersNormalised:
        """Normalize account-update input into types the Python SDK expects.

        Actions performed:
        - Validates and parses `params` against the Pydantic schema.
        - Resolves `account_id` (defaults to operator account if not provided).
        - Builds an `AccountUpdateParams` instance with only the fields that are set.
        - Normalizes optional scheduling parameters when `is_scheduled` is True.

        Args:
            params: Raw account update parameters.
            context: Application context used for resolving defaults.
            client: Hedera `Client` used to access operator account when needed.

        Returns:
            UpdateAccountParametersNormalised: Parameters converted to SDK-compatible types.

        Raises:
            ValueError: If validation fails or account ID cannot be resolved.
        """
        from hiero_sdk_python.account.account_update_transaction import (
            AccountUpdateParams,
        )

        parsed_params: UpdateAccountParameters = cast(
            UpdateAccountParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, UpdateAccountParameters
            ),
        )

        # Resolve account ID (default to operator if not provided)
        account_id = AccountId.from_string(
            AccountResolver.resolve_account(parsed_params.account_id, context, client)
        )

        # Build AccountUpdateParams with only the fields that are provided
        account_params = AccountUpdateParams(account_id=account_id)

        if parsed_params.account_memo is not None:
            account_params.account_memo = parsed_params.account_memo

        # FIXME: commented out - SDK does not support these fields yet
        """
        if parsed_params.max_automatic_token_associations is not None:
            account_params.max_automatic_token_associations = (
                parsed_params.max_automatic_token_associations
            )
        if parsed_params.staked_account_id is not None:
            account_params.staked_account_id = AccountId.from_string(
                parsed_params.staked_account_id
            )

        if parsed_params.decline_staking_reward is not None:
            account_params.decline_reward = parsed_params.decline_staking_reward
        """

        # Normalize scheduling parameters (if present and is_scheduled = True)
        scheduling_params: ScheduleCreateParams | None = None
        if getattr(parsed_params, "scheduling_params", None):
            if parsed_params.scheduling_params.is_scheduled:
                scheduling_params = await HederaParameterNormaliser.normalise_scheduled_transaction_params(
                    parsed_params.scheduling_params, context, client
                )

        return UpdateAccountParametersNormalised(
            account_params=account_params,
            scheduling_params=scheduling_params,
        )

    @staticmethod
    async def normalise_submit_topic_message(
        params: SubmitTopicMessageParameters,
        context: Context,
        client: Client,
    ) -> SubmitTopicMessageParametersNormalised:
        """Normalize submit topic message parameters.

        This function:
          - Validates and parses the raw parameters using the SubmitTopicMessageParameters schema.
          - Converts the topic_id string to basic_types_pb2.TopicID.
          - Normalizes optional scheduling parameters when is_scheduled is True.

        Args:
            params: Raw topic message submission parameters provided by the user.
            context: Application context (contains environment configuration).
            client: Hedera Client instance used for resolving scheduling parameters.

        Returns:
            SubmitTopicMessageParametersNormalised: A validated, SDK-ready parameter object
            with topic_id converted to basic_types_pb2.TopicID and scheduling params normalized.

        Raises:
            ValueError: If parameter validation fails.
        """

        # Validate and parse parameters
        parsed_params: SubmitTopicMessageParameters = cast(
            SubmitTopicMessageParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, SubmitTopicMessageParameters
            ),
        )

        # Normalize scheduling parameters (if present and is_scheduled = True)
        scheduling_params: ScheduleCreateParams | None = None
        if getattr(parsed_params, "scheduling_params", None):
            if parsed_params.scheduling_params.is_scheduled:
                scheduling_params = await HederaParameterNormaliser.normalise_scheduled_transaction_params(
                    parsed_params.scheduling_params, context, client
                )

        return SubmitTopicMessageParametersNormalised(
            topic_id=TopicId.from_string(parsed_params.topic_id),
            message=parsed_params.message,
            transaction_memo=parsed_params.transaction_memo,
            scheduling_params=scheduling_params,
        )

    @staticmethod
    def normalise_delete_topic(
        params: DeleteTopicParameters,
    ) -> DeleteTopicParametersNormalised:
        """Normalise delete topic parameters to a format compatible with Python SDK.

        Args:
            params: Raw delete topic parameters.

        Returns:
            DeleteTopicParametersNormalised: Normalised delete topic parameters
            ready to be used in Hedera transactions.

        Raises:
            ValueError: If validation fails.
        """

        # First, validate against the basic schema
        parsed_params: DeleteTopicParameters = cast(
            DeleteTopicParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, DeleteTopicParameters
            ),
        )

        if not AccountResolver.is_hedera_address(parsed_params.topic_id):
            raise ValueError("Topic ID must be a Hedera address")

        parsed_topic_id = TopicId.from_string(parsed_params.topic_id)

        return DeleteTopicParametersNormalised(topic_id=parsed_topic_id)

    @staticmethod
    def normalise_get_transaction_record_params(
        params: TransactionRecordQueryParameters,
    ) -> TransactionRecordQueryParametersNormalised:
        """Normalize transaction record query parameters.

        This method validates the input parameters and converts transaction IDs
        from SDK-style format (e.g., "0.0.4177806@1755169980.051721264")
        to mirror-node style format (e.g., "0.0.4177806-1755169980-051721264").

        Args:
            params: Raw transaction record query parameters.

        Returns:
            TransactionRecordQueryParametersNormalised: Normalized parameters
            with transaction ID in mirror-node format.

        Raises:
            ValueError: If transaction_id is missing or in an invalid format.
        """
        import re

        parsed_params: TransactionRecordQueryParameters = cast(
            TransactionRecordQueryParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, TransactionRecordQueryParameters
            ),
        )

        if not parsed_params.transaction_id:
            raise ValueError("transactionId is required")

        # Regex patterns for different transaction ID formats
        mirror_node_style_regex = re.compile(r"^\d+\.\d+\.\d+-\d+-\d+$")
        sdk_style_regex = re.compile(r"^(\d+\.\d+\.\d+)@(\d+)\.(\d+)$")

        transaction_id: str

        # Check if already in mirror-node style
        if mirror_node_style_regex.match(parsed_params.transaction_id):
            transaction_id = parsed_params.transaction_id
        else:
            # Try to match SDK-style format
            match = sdk_style_regex.match(parsed_params.transaction_id)
            if not match:
                raise ValueError(
                    f"Invalid transactionId format: {parsed_params.transaction_id}"
                )

            # Convert from SDK style to mirror-node style
            account_id, seconds, nanos = match.groups()
            transaction_id = f"{account_id}-{seconds}-{nanos}"

        return TransactionRecordQueryParametersNormalised(
            transaction_id=transaction_id,
            nonce=parsed_params.nonce,
        )

    @staticmethod
    async def normalise_transfer_hbar_with_allowance(
        params: TransferHbarWithAllowanceParameters,
        context: Context,
        client: Client,
    ) -> TransferHbarWithAllowanceParametersNormalised:
        """Normalize parameters for transferring HBAR with allowance.

        Args:
            params: The raw input parameters.

        Returns:
            The normalized parameters ready for transaction building.
        """
        parsed_params: TransferHbarWithAllowanceParameters = cast(
            TransferHbarWithAllowanceParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, TransferHbarWithAllowanceParameters
            ),
        )

        hbar_approved_transfers: dict[AccountId, int] = {}
        total_tinybars = 0

        if not parsed_params.source_account_id:
            raise ValueError("source_account_id is required for allowance transfers")

        owner_id = AccountId.from_string(parsed_params.source_account_id)

        # Process recipients
        for transfer in parsed_params.transfers:
            amount_hbar = Hbar(transfer.amount)
            amount_tiny = amount_hbar.to_tinybars()

            if amount_tiny <= 0:
                raise ValueError(f"Invalid transfer amount: {transfer.amount}")

            total_tinybars += amount_tiny

            recipient_id = AccountId.from_string(transfer.account_id)

            current_val = hbar_approved_transfers.get(recipient_id, 0)
            hbar_approved_transfers[recipient_id] = current_val + amount_tiny

        # Add the owner deduction (negative amount)
        current_owner_val = hbar_approved_transfers.get(owner_id, 0)
        hbar_approved_transfers[owner_id] = current_owner_val - total_tinybars

        # Normalize scheduling parameters (if present and is_scheduled = True)
        scheduling_params: ScheduleCreateParams | None = None
        if getattr(parsed_params, "scheduling_params", None):
            if parsed_params.scheduling_params.is_scheduled:
                scheduling_params = await HederaParameterNormaliser.normalise_scheduled_transaction_params(
                    parsed_params.scheduling_params, context, client
                )

        return TransferHbarWithAllowanceParametersNormalised(
            hbar_approved_transfers=hbar_approved_transfers,
            transaction_memo=parsed_params.transaction_memo,
            scheduling_params=scheduling_params,
        )

    @staticmethod
    async def normalise_update_topic(
        params: UpdateTopicParameters,
        context: Context,
        client: Client,
    ) -> UpdateTopicParametersNormalised:
        """Normalize parameters for updating a topic.

        Args:
            params: The raw input parameters.
            context: The runtime context.
            client: The Hedera client.

        Returns:
            The normalized parameters are ready for transaction building.
        """
        parsed_params: UpdateTopicParameters = cast(
            UpdateTopicParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, UpdateTopicParameters
            ),
        )
        topic_id = TopicId.from_string(parsed_params.topic_id)

        # Determine the default user public key (operator key)
        user_public_key = None
        if client.operator_private_key:
            user_public_key = client.operator_private_key.public_key()

        # Resolve Keys
        admin_key = HederaParameterNormaliser.resolve_key(
            parsed_params.admin_key, user_public_key
        )
        submit_key = HederaParameterNormaliser.resolve_key(
            parsed_params.submit_key, user_public_key
        )

        # Resolve Auto Renew Account
        auto_renew_account = None
        if parsed_params.auto_renew_account_id:
            auto_renew_account = AccountId.from_string(
                parsed_params.auto_renew_account_id
            )

        # Resolve Expiration Time
        expiration_time = None
        if parsed_params.expiration_time:
            if isinstance(parsed_params.expiration_time, datetime):
                expiration_time = parsed_params.expiration_time
            else:
                expiration_time = datetime.fromisoformat(
                    str(parsed_params.expiration_time).replace("Z", "+00:00")
                )

        return UpdateTopicParametersNormalised(
            topic_id=topic_id,
            memo=parsed_params.topic_memo,
            admin_key=admin_key,
            submit_key=submit_key,
            auto_renew_account=auto_renew_account,
            auto_renew_period=parsed_params.auto_renew_period,
            expiration_time=expiration_time,
        )

    @staticmethod
    def normalise_get_token_info(
        params: GetTokenInfoParameters,
    ) -> GetTokenInfoParameters:
        """Normalize parameters for getting token info.

        Args:
            params: The raw input parameters.

        Returns:
            The validated parameters.

        Raises:
            ValueError: If token_id is missing.
        """
        parsed_params: GetTokenInfoParameters = cast(
            GetTokenInfoParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, GetTokenInfoParameters
            ),
        )
        if not parsed_params.token_id:
            raise ValueError("Token ID is required to fetch token info.")
        return parsed_params

    @staticmethod
    async def normalise_dissociate_token_params(
        params: DissociateTokenParameters,
        context: Context,
        client: Client,
    ) -> DissociateTokenParametersNormalised:
        """Normalize parameters for dissociating tokens.

        Args:
            params: The raw input parameters.
            context: The runtime context.
            client: The Hedera client.

        Returns:
            The normalized parameters are ready for transaction building.
        """
        parsed_params: DissociateTokenParameters = cast(
            DissociateTokenParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, DissociateTokenParameters
            ),
        )

        # Resolve Account ID (default to operator if not provided)
        account_id_str = parsed_params.account_id
        if not account_id_str and client.operator_account_id:
            account_id_str = str(client.operator_account_id)

        if not account_id_str:
            raise ValueError("Account ID is required for token dissociation.")

        account_id = AccountId.from_string(account_id_str)

        # Resolve Token IDs
        token_ids = [TokenId.from_string(t_id) for t_id in parsed_params.token_ids]

        # Normalize scheduling parameters (if present and is_scheduled = True)
        scheduling_params: ScheduleCreateParams | None = None
        if getattr(parsed_params, "scheduling_params", None):
            if parsed_params.scheduling_params.is_scheduled:
                scheduling_params = await HederaParameterNormaliser.normalise_scheduled_transaction_params(
                    parsed_params.scheduling_params, context, client
                )

        return DissociateTokenParametersNormalised(
            token_ids=token_ids,
            account_id=account_id,
            transaction_memo=parsed_params.transaction_memo,
            scheduling_params=scheduling_params,
        )
