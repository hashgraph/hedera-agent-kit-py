from datetime import datetime
from decimal import Decimal
from typing import Optional, Union, cast, Any, Type, List

from hiero_sdk_python.contract.contract_id import ContractId
from hiero_sdk_python import (
    AccountId,
    PublicKey,
    Timestamp,
    Client,
    Hbar,
    TopicId,
    TokenId,
    SupplyType,
    HbarAllowance,
    TokenAllowance,
    TokenNftAllowance,
    TokenType,
)
from hiero_sdk_python.schedule.schedule_create_transaction import ScheduleCreateParams
from hiero_sdk_python.schedule.schedule_id import ScheduleId
from hiero_sdk_python.tokens.token_create_transaction import TokenKeys, TokenParams
from hiero_sdk_python.tokens.token_transfer import TokenTransfer
from pydantic import BaseModel, ValidationError
from web3 import Web3

from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.hedera_utils import to_tinybars, to_base_unit
from hedera_agent_kit.shared.hedera_utils.mirrornode.hedera_mirrornode_service_interface import (
    IHederaMirrornodeService,
)
from hedera_agent_kit.shared.hedera_utils.mirrornode.types import TokenInfo
from hedera_agent_kit.shared.parameter_schemas import (
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
    AccountTokenBalancesQueryParameters,
    AccountTokenBalancesQueryParametersNormalised,
    AssociateTokenParameters,
    AssociateTokenParametersNormalised,
    GetTopicInfoParameters,
    ExchangeRateQueryParameters,
    ContractExecuteTransactionParametersNormalised,
    CreateERC20Parameters,
    TransferERC20Parameters,
    TransferERC721Parameters,
    CreateERC721Parameters,
    MintERC721Parameters,
    TransactionRecordQueryParameters,
    TransactionRecordQueryParametersNormalised,
    CreateFungibleTokenParametersNormalised,
    CreateFungibleTokenParameters,
    UpdateTopicParameters,
    UpdateTopicParametersNormalised,
    MintFungibleTokenParameters,
    MintFungibleTokenParametersNormalised,
)
from hedera_agent_kit.shared.parameter_schemas.token_schema import (
    AirdropFungibleTokenParameters,
    AirdropFungibleTokenParametersNormalised,
    NftApprovedTransferNormalised,
)

from hedera_agent_kit.shared.parameter_schemas.account_schema import (
    AccountQueryParameters,
    AccountQueryParametersNormalised,
    TransferHbarWithAllowanceParametersNormalised,
    TransferHbarWithAllowanceParameters,
    DeleteHbarAllowanceParameters,
    ApproveHbarAllowanceParametersNormalised,
    DeleteTokenAllowanceParameters,
    TokenApproval,
    ApproveTokenAllowanceParameters,
    ApproveTokenAllowanceParametersNormalised,
    ScheduleDeleteTransactionParameters,
    ScheduleDeleteTransactionParametersNormalised,
    ApproveHbarAllowanceParameters,
)
from hedera_agent_kit.shared.parameter_schemas.token_schema import (
    ApproveNftAllowanceParameters,
    ApproveNftAllowanceParametersNormalised,
    GetTokenInfoParameters,
    DissociateTokenParameters,
    DissociateTokenParametersNormalised,
    CreateNonFungibleTokenParameters,
    MintNonFungibleTokenParametersNormalised,
    MintNonFungibleTokenParameters,
    CreateNonFungibleTokenParametersNormalised,
    TransferFungibleTokenWithAllowanceParameters,
    TransferFungibleTokenWithAllowanceParametersNormalised,
    TransferNonFungibleTokenWithAllowanceParameters,
    TransferNonFungibleTokenWithAllowanceParametersNormalised,
)

from hedera_agent_kit.shared.utils.account_resolver import AccountResolver
from hedera_agent_kit.shared.constants.contracts import (
    ERC721_MINT_FUNCTION_ABI,
    ERC721_MINT_FUNCTION_NAME,
)
from hedera_agent_kit.shared.hedera_utils.mirrornode import get_mirrornode_service
from hedera_agent_kit.shared.utils import ledger_id_from_network
from hedera_agent_kit.shared.utils.ledger_id import LedgerId
from hedera_agent_kit.shared.utils.account_resolver import AccountResolver


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
            f'Field "{".".join(str(loc) for loc in err["loc"]) or "root"}" - {err["msg"]}'
            for err in error.errors()
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
    def normalise_schedule_delete_transaction(
        params: ScheduleDeleteTransactionParameters,
    ) -> ScheduleDeleteTransactionParametersNormalised:
        """Normalise schedule delete transaction parameters.

        Args:
            params: Raw schedule delete parameters.

        Returns:
            ScheduleDeleteTransactionParametersNormalised: Normalised parameters.
        """
        parsed_params: ScheduleDeleteTransactionParameters = cast(
            ScheduleDeleteTransactionParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, ScheduleDeleteTransactionParameters
            ),
        )

        return ScheduleDeleteTransactionParametersNormalised(
            schedule_id=ScheduleId.from_string(parsed_params.schedule_id)
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
            return PublicKey.from_string(raw_value)
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

    @staticmethod
    def normalise_account_token_balances_params(
        params: AccountTokenBalancesQueryParameters,
        context: Context,
        client: Client,
    ) -> AccountTokenBalancesQueryParametersNormalised:
        """Normalise account token balances query parameters.

        If an account_id is provided, it is used directly.
        Otherwise, the default account from AccountResolver is used.
        """
        parsed_params: AccountTokenBalancesQueryParameters = cast(
            AccountTokenBalancesQueryParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, AccountTokenBalancesQueryParameters
            ),
        )

        if parsed_params.account_id is None:
            resolved_account_id = AccountResolver.get_default_account(context, client)
        else:
            resolved_account_id = parsed_params.account_id

        return AccountTokenBalancesQueryParametersNormalised(
            account_id=resolved_account_id,
            token_id=parsed_params.token_id,
        )

    @classmethod
    def normalise_get_account_query(cls, params) -> AccountQueryParametersNormalised:
        """Parse and validate account query parameters"""
        parsed_params: AccountQueryParameters = cast(
            AccountQueryParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, AccountQueryParameters
            ),
        )
        return AccountQueryParametersNormalised(account_id=parsed_params.account_id)

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
          - Resolves admin and submit keys if provided (supports boolean or string values).
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
            admin_key=None,
        )

        # Resolve admin key if provided
        normalised.admin_key = HederaParameterNormaliser.resolve_key(
            parsed_params.admin_key, account_public_key
        )

        # Resolve submit key if provided
        normalised.submit_key = HederaParameterNormaliser.resolve_key(
            parsed_params.submit_key, account_public_key
        )

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
    async def normalise_mint_erc721_params(
        params: MintERC721Parameters,
        context: Context,
        mirrornode_service: IHederaMirrornodeService,
        client: Client,
    ) -> ContractExecuteTransactionParametersNormalised:
        """Normalise parameters for minting an ERC721 token via ContractExecuteTransaction.

        Encodes a call to the ERC721 `safeMint(address to)` function on the target contract.
        The `to_address` parameter is optional and will default to the context's default
        account (operator or provided user account) if not supplied.
        """
        # Parse and validate with schema
        parsed_params: MintERC721Parameters = cast(
            MintERC721Parameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, MintERC721Parameters
            ),
        )

        # Resolve recipient address (Hedera account ID or EVM) -> EVM address string
        to_address_input = getattr(parsed_params, "to_address", None)
        target_address = (
            to_address_input
            if to_address_input
            else AccountResolver.get_default_account(context, client)
        )

        if AccountResolver.is_hedera_address(target_address):
            resolved_to_evm = await AccountResolver.get_hedera_evm_address(
                target_address, mirrornode_service
            )
        else:
            resolved_to_evm = target_address

        # Encode function call data for safeMint(address)
        w3 = Web3()
        # Ensure EVM address is in checksum format as required by web3.py
        checksummed_to = w3.to_checksum_address(resolved_to_evm)
        contract = w3.eth.contract(abi=ERC721_MINT_FUNCTION_ABI)
        encoded_data = contract.encode_abi(
            abi_element_identifier=ERC721_MINT_FUNCTION_NAME, args=[checksummed_to]
        )
        function_parameters = bytes.fromhex(encoded_data[2:])

        # Scheduling (optional)
        scheduling_params: ScheduleCreateParams | None = None
        if getattr(parsed_params, "scheduling_params", None):
            if parsed_params.scheduling_params.is_scheduled:
                scheduling_params = await HederaParameterNormaliser.normalise_scheduled_transaction_params(
                    parsed_params.scheduling_params, context, client
                )

        # Resolve contract to Hedera ContractId from either 0x address or 0.0.x
        if AccountResolver.is_hedera_address(parsed_params.contract_id):
            contract_id_str = parsed_params.contract_id
        else:
            contract_id_str = await AccountResolver.get_hedera_account_id(
                parsed_params.contract_id, mirrornode_service
            )
        return ContractExecuteTransactionParametersNormalised(
            contract_id=ContractId.from_string(contract_id_str),
            function_parameters=function_parameters,
            gas=3_000_000,  # TODO: consider configurability
            scheduling_params=scheduling_params,
        )

    @staticmethod
    async def normalise_create_erc721_params(
        params: CreateERC721Parameters,
        factory_address: str,
        ERC721_FACTORY_ABI: list[str],
        factory_contract_function_name: str,
        context: Context,
        client: Client,
    ) -> ContractExecuteTransactionParametersNormalised:
        """Normalise ERC721 creation parameters for BaseERC721Factory contract deployment.

        Prepares encoded function call data for `deployToken(name, symbol, baseURI)` and
        optionally includes scheduling parameters when requested.

        Args:
            params: Raw ERC721 creation parameters.
            factory_address: The address/ID of the ERC721 factory contract.
            ERC721_FACTORY_ABI: ABI of the BaseERC721Factory contract.
            factory_contract_function_name: Function to invoke (e.g., 'deployToken').
            context: Application context.
            client: Active Hedera client instance.

        Returns:
            ContractExecuteTransactionParametersNormalised
        """
        parsed_params: CreateERC721Parameters = cast(
            CreateERC721Parameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, CreateERC721Parameters
            ),
        )

        w3 = Web3()
        contract = w3.eth.contract(abi=ERC721_FACTORY_ABI)
        encoded_data = contract.encode_abi(
            abi_element_identifier=factory_contract_function_name,
            args=[
                parsed_params.token_name,
                parsed_params.token_symbol,
                parsed_params.base_uri,
            ],
        )
        function_parameters = bytes.fromhex(encoded_data[2:])

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
    async def normalise_transfer_erc20_params(
        params: TransferERC20Parameters,
        factory_contract_abi: list[dict],
        factory_contract_function_name: str,
        context: Context,
        mirrornode_service: IHederaMirrornodeService,
        client: Client,
    ) -> ContractExecuteTransactionParametersNormalised:
        """Normalise ERC20 transfer parameters for contract execution.

        This method mirrors the TypeScript `normaliseTransferERC20Params` logic and prepares
        the encoded contract function call for transferring ERC20 tokens.

        Args:
            params: Raw ERC20 transfer parameters.
            factory_contract_abi: ABI of the ERC20 contract.
            factory_contract_function_name: Function to invoke (e.g., 'transfer').
            context: Application context.
            mirrornode_service: Mirror node service for address resolution.
            client: Active Hedera client instance.

        Returns:
            ContractExecuteTransactionParametersNormalised: Normalised parameters ready for execution.
        """
        # Validate and parse parameters
        parsed_params: TransferERC20Parameters = cast(
            TransferERC20Parameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, TransferERC20Parameters
            ),
        )

        # Resolve recipient address to EVM address
        recipient_address = await AccountResolver.get_hedera_evm_address(
            parsed_params.recipient_address, mirrornode_service
        )

        # Resolve contract ID to Hedera account ID
        contract_id_str = await AccountResolver.get_hedera_account_id(
            parsed_params.contract_id, mirrornode_service
        )
        contract_id = ContractId.from_string(contract_id_str)

        # Encode the function call
        w3 = Web3()
        # Convert to checksum address as required by Web3.py
        checksummed_recipient = w3.to_checksum_address(recipient_address)
        contract = w3.eth.contract(abi=factory_contract_abi)
        encoded_data = contract.encode_abi(
            abi_element_identifier=factory_contract_function_name,
            args=[
                checksummed_recipient,
                parsed_params.amount,
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
            contract_id=contract_id,
            function_parameters=function_parameters,
            gas=100_000,
            scheduling_params=scheduling_params,
        )

    @staticmethod
    async def normalise_transfer_erc721_params(
        params: TransferERC721Parameters,
        factory_contract_abi: list[dict],
        factory_contract_function_name: str,
        context: Context,
        mirrornode_service: IHederaMirrornodeService,
        client: Client,
    ) -> ContractExecuteTransactionParametersNormalised:
        """Normalise ERC721 transfer parameters for contract execution.

        This method mirrors the TypeScript `normaliseTransferERC721Params` logic and prepares
        the encoded contract function call for transferring ERC721 tokens (NFTs).

        Args:
            params: Raw ERC721 transfer parameters.
            factory_contract_abi: ABI of the ERC721 contract.
            factory_contract_function_name: Function to invoke (e.g., 'transferFrom').
            context: Application context.
            mirrornode_service: Mirror node service for address resolution.
            client: Active Hedera client instance.

        Returns:
            ContractExecuteTransactionParametersNormalised: Normalised parameters ready for execution.
        """
        # Validate and parse parameters
        parsed_params: TransferERC721Parameters = cast(
            TransferERC721Parameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, TransferERC721Parameters
            ),
        )

        # Resolve from_address using AccountResolver pattern (defaults to operator)
        resolved_from_address = AccountResolver.resolve_account(
            parsed_params.from_address, context, client
        )
        from_address = await AccountResolver.get_hedera_evm_address(
            resolved_from_address, mirrornode_service
        )

        # Resolve to_address to EVM address
        to_address = await AccountResolver.get_hedera_evm_address(
            parsed_params.to_address, mirrornode_service
        )

        # Resolve contract ID to Hedera account ID
        contract_id_str = await AccountResolver.get_hedera_account_id(
            parsed_params.contract_id, mirrornode_service
        )
        contract_id = ContractId.from_string(contract_id_str)

        # Encode the function call
        w3 = Web3()
        # Convert both addresses to checksum format as required by Web3.py
        checksummed_from = w3.to_checksum_address(from_address)
        checksummed_to = w3.to_checksum_address(to_address)
        contract = w3.eth.contract(abi=factory_contract_abi)
        encoded_data = contract.encode_abi(
            abi_element_identifier=factory_contract_function_name,
            args=[
                checksummed_from,
                checksummed_to,
                parsed_params.token_id,
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
            contract_id=contract_id,
            function_parameters=function_parameters,
            gas=100_000,
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
    def normalise_associate_token(
        params: AssociateTokenParameters,
        context: Context,
        client: Client,
    ) -> AssociateTokenParametersNormalised:
        """Normalise token association parameters to a format compatible with Python SDK.

        Args:
            params: Raw token association parameters.
            context: Application context for resolving accounts.
            client: Hedera Client instance used for account resolution.

        Returns:
            AssociateTokenParametersNormalised: Normalised token association parameters
            ready to be used in Hedera transactions.

        Raises:
            ValueError: If token IDs are invalid or account ID cannot be determined.
        """
        from hiero_sdk_python import TokenId

        parsed_params: AssociateTokenParameters = cast(
            AssociateTokenParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, AssociateTokenParameters
            ),
        )

        # Resolve account ID (default to operator if not provided)
        account_id = AccountId.from_string(
            AccountResolver.resolve_account(parsed_params.account_id, context, client)
        )

        # Parse token IDs
        token_ids = [
            TokenId.from_string(token_id) for token_id in parsed_params.token_ids
        ]

        return AssociateTokenParametersNormalised(
            account_id=account_id,
            token_ids=token_ids,
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
    async def normalise_mint_non_fungible_token_params(
        params: MintNonFungibleTokenParameters,
        context: Context,
        client: Client,
    ) -> MintNonFungibleTokenParametersNormalised:
        """Normalise mint non-fungible token parameters.

        Args:
            params: Raw mint parameters.
            context: Application context.
            client: Hedera client.

        Returns:
            MintNonFungibleTokenParametersNormalised: Normalised parameters.
        """
        parsed_params: MintNonFungibleTokenParameters = cast(
            MintNonFungibleTokenParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, MintNonFungibleTokenParameters
            ),
        )

        metadata = [uri.encode("utf-8") for uri in parsed_params.uris]

        # Normalize scheduling parameters (if present and is_scheduled = True)
        scheduling_params: ScheduleCreateParams | None = None
        if getattr(parsed_params, "scheduling_params", None):
            if parsed_params.scheduling_params.is_scheduled:
                scheduling_params = await HederaParameterNormaliser.normalise_scheduled_transaction_params(
                    parsed_params.scheduling_params, context, client
                )

        return MintNonFungibleTokenParametersNormalised(
            token_id=TokenId.from_string(parsed_params.token_id),
            metadata=metadata,
            scheduling_params=scheduling_params,
        )

    @staticmethod
    def normalise_approve_hbar_allowance(
        params: ApproveHbarAllowanceParameters,
        context: Context,
        client: Client,
    ) -> ApproveHbarAllowanceParametersNormalised:
        """Normalise approve HBAR allowance parameters.

        Args:
            params: Raw approve HBAR allowance parameters.
            context: Application context for resolving accounts.
            client: Hedera Client instance used for account resolution.

        Returns:
            ApproveHbarAllowanceParametersNormalised: Normalised parameters.
        """
        parsed_params: ApproveHbarAllowanceParameters = cast(
            ApproveHbarAllowanceParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, ApproveHbarAllowanceParameters
            ),
        )

        owner_account_id = AccountResolver.resolve_account(
            parsed_params.owner_account_id, context, client
        )

        spender_account_id = parsed_params.spender_account_id

        amount = Hbar(parsed_params.amount)
        if amount.to_tinybars() < 0:
            raise ValueError(f"Invalid allowance amount: {parsed_params.amount}")

        return ApproveHbarAllowanceParametersNormalised(
            hbar_allowances=[
                HbarAllowance(
                    owner_account_id=AccountId.from_string(owner_account_id),
                    spender_account_id=AccountId.from_string(spender_account_id),
                    amount=amount.to_tinybars(),
                )
            ],
            transaction_memo=parsed_params.transaction_memo,
        )

    @staticmethod
    def normalise_approve_nft_allowance(
        params: ApproveNftAllowanceParameters,
        context: Context,
        client: Client,
    ) -> ApproveNftAllowanceParametersNormalised:
        """Normalise approve NFT allowance parameters.

        Args:
            params: Raw approve NFT allowance parameters.
            context: Application context for resolving accounts.
            client: Hedera Client instance used for account resolution.

        Returns:
            ApproveNftAllowanceParametersNormalised: Normalised parameters.
        """
        parsed_params: ApproveNftAllowanceParameters = cast(
            ApproveNftAllowanceParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, ApproveNftAllowanceParameters
            ),
        )

        owner_account_id = AccountResolver.resolve_account(
            parsed_params.owner_account_id, context, client
        )

        spender_account_id = parsed_params.spender_account_id
        token_id = TokenId.from_string(parsed_params.token_id)

        # Validate that either all_serials is true or serial_numbers is provided
        if not parsed_params.all_serials and not parsed_params.serial_numbers:
            raise ValueError(
                "Either all_serials must be true or serial_numbers must be provided"
            )

        # If all_serials is true, serial_numbers should not be provided
        if parsed_params.all_serials and parsed_params.serial_numbers:
            raise ValueError("Cannot specify both all_serials=true and serial_numbers")

        # Create the NFT allowance
        nft_allowance = TokenNftAllowance(
            token_id=token_id,
            owner_account_id=AccountId.from_string(owner_account_id),
            spender_account_id=AccountId.from_string(spender_account_id),
            approved_for_all=parsed_params.all_serials,
            serial_numbers=parsed_params.serial_numbers or [],
        )

        return ApproveNftAllowanceParametersNormalised(
            nft_allowances=[nft_allowance],
            transaction_memo=parsed_params.transaction_memo,
        )

    @staticmethod
    async def normalise_airdrop_fungible_token_params(
        params: AirdropFungibleTokenParameters,
        context: Context,
        client: Client,
        mirrornode_service: IHederaMirrornodeService,
    ) -> AirdropFungibleTokenParametersNormalised:
        """Normalise airdrop fungible token parameters.

        Args:
            params: Raw airdrop parameters.
            context: Application context.
            client: Hedera Client.
            mirrornode_service: Mirror node service.

        Returns:
            AirdropFungibleTokenParametersNormalised: Normalised parameters.
        """
        parsed_params: AirdropFungibleTokenParameters = cast(
            AirdropFungibleTokenParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, AirdropFungibleTokenParameters
            ),
        )

        source_account_id = AccountResolver.resolve_account(
            parsed_params.source_account_id, context, client
        )

        token_info: TokenInfo = await mirrornode_service.get_token_info(
            parsed_params.token_id
        )
        token_decimals = int(token_info.get("decimals", -1))
        if token_decimals < 0:
            raise ValueError(
                f"Unable to retrieve token decimals for token ID {parsed_params.token_id}"
            )

        token_transfers: List[TokenTransfer] = []
        total_amount = 0

        for recipient in parsed_params.recipients:
            amount_raw = Decimal(str(recipient.amount))

            if amount_raw <= 0:
                raise ValueError(f"Invalid recipient amount: {recipient.amount}")

            # Convert correctly using integer-safe math
            amount = to_base_unit(amount_raw, token_decimals)
            amount_int = int(amount)

            if amount_int == 0:
                raise ValueError(
                    f"Amount too small after scaling (raw={recipient.amount}, decimals={token_decimals})"
                )

            total_amount += amount_int

            token_transfers.append(
                TokenTransfer(
                    token_id=TokenId.from_string(parsed_params.token_id),
                    account_id=AccountId.from_string(recipient.account_id),
                    amount=amount_int,
                )
            )

        # Sender negative total
        token_transfers.append(
            TokenTransfer(
                token_id=TokenId.from_string(parsed_params.token_id),
                account_id=AccountId.from_string(source_account_id),
                amount=-total_amount,
            )
        )

        # Handle optional scheduling
        scheduling_params = None
        if getattr(parsed_params, "scheduling_params", None):
            if parsed_params.scheduling_params.is_scheduled:
                scheduling_params = await HederaParameterNormaliser.normalise_scheduled_transaction_params(
                    parsed_params.scheduling_params, context, client
                )

        return AirdropFungibleTokenParametersNormalised(
            token_transfers=token_transfers,
            scheduling_params=scheduling_params,
            transaction_memo=parsed_params.transaction_memo,
        )

    @staticmethod
    async def normalise_create_fungible_token_params(
        params: CreateFungibleTokenParameters,
        context: Context,
        client: Client,
        mirrornode: IHederaMirrornodeService,
    ) -> CreateFungibleTokenParametersNormalised:
        """Normalize parameters for creating a fungible token."""

        # Parse + validate against schema
        parsed_params: CreateFungibleTokenParameters = cast(
            CreateFungibleTokenParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, CreateFungibleTokenParameters
            ),
        )

        # Treasury resolution
        default_account_id = (
            str(client.operator_account_id) if client.operator_account_id else None
        )

        treasury_account_id = parsed_params.treasury_account_id or default_account_id

        if not treasury_account_id:
            raise ValueError("Must include treasury account ID")

        # Resolve decimals + supply units
        decimals = parsed_params.decimals or 0
        initial_supply = int((parsed_params.initial_supply or 0) * (10**decimals))

        if parsed_params.max_supply is not None and parsed_params.supply_type == 0:
            raise ValueError("Cannot set max supply and INFINITE supply type")

        # Resolve Supply Type
        if parsed_params.supply_type is None:
            supply_type = SupplyType.FINITE  # SPEC DEFAULT
        else:
            if parsed_params.supply_type in (0, SupplyType.INFINITE, "infinite"):
                supply_type = SupplyType.INFINITE
            elif parsed_params.supply_type in (1, SupplyType.FINITE, "finite"):
                supply_type = SupplyType.FINITE
            else:
                raise ValueError("Invalid supply_type; must be finite or infinite.")

        max_supply = None

        if supply_type == SupplyType.FINITE:
            # default 1 million tokens (in whole units)
            raw_max_supply = parsed_params.max_supply or 1_000_000
            max_supply = int(raw_max_supply * (10**decimals))

            # Hedera requires NON-ZERO initial supply for finite tokens
            if initial_supply == 0:
                initial_supply = 1 * (10**decimals)

        # Validation
        if max_supply is not None and initial_supply > max_supply:
            raise ValueError(
                f"Initial supply ({initial_supply}) cannot exceed max supply ({max_supply})"
            )

        if parsed_params.is_supply_key is None:
            # default: true when supply finite OR max_supply provided
            is_supply_key = supply_type == SupplyType.FINITE
        else:
            is_supply_key = parsed_params.is_supply_key

        supply_key: Optional[PublicKey] = None

        if is_supply_key:
            public_key = None
            try:
                account_info = await mirrornode.get_account(treasury_account_id)
                if account_info.get("account_public_key"):
                    public_key = account_info["account_public_key"]
            except Exception:
                pass

            if not public_key and client.operator_private_key.public_key():
                public_key = client.operator_private_key.public_key().to_string_der()

            if public_key:
                supply_key = PublicKey.from_string(public_key)

        # Normalize scheduling parameters (if present and is_scheduled = True)
        scheduling_params: ScheduleCreateParams | None = None
        if getattr(parsed_params, "scheduling_params", None):
            if parsed_params.scheduling_params.is_scheduled:
                scheduling_params = await HederaParameterNormaliser.normalise_scheduled_transaction_params(
                    parsed_params.scheduling_params, context, client
                )

        # Construct TokenParams
        token_params = TokenParams(
            token_name=parsed_params.token_name,
            token_symbol=parsed_params.token_symbol,
            decimals=decimals,
            initial_supply=initial_supply,
            treasury_account_id=AccountId.from_string(treasury_account_id),
            supply_type=supply_type,
            max_supply=max_supply,
            auto_renew_account_id=AccountId.from_string(default_account_id),
        )

        token_keys = TokenKeys(supply_key=supply_key) if supply_key else None

        return CreateFungibleTokenParametersNormalised(
            token_params=token_params,
            keys=token_keys,
            scheduling_params=scheduling_params,
        )

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
            params: The raw input parameters for the HBAR transfer with allowance.
            context: Application context for resolving defaults and configuration.
            client: Hedera Client instance used for transaction execution and resolution.

        Returns:
            The normalized parameters are ready for transaction building.
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

    @staticmethod
    async def normalise_mint_fungible_token_params(
        params: MintFungibleTokenParameters,
        context: Context,
        client: Client,
        mirrornode_service: IHederaMirrornodeService,
    ) -> MintFungibleTokenParametersNormalised:
        """Normalize mint fungible token parameters.

        Args:
            params: Raw mint parameters.
            context: Application context.
            client: Hedera client.
            mirrornode_service: Mirror node service.

        Returns:
            MintFungibleTokenParametersNormalised: Normalized parameters.
        """
        parsed_params: MintFungibleTokenParameters = cast(
            MintFungibleTokenParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, MintFungibleTokenParameters
            ),
        )

        token_info = await mirrornode_service.get_token_info(parsed_params.token_id)

        if not token_info.get("decimals"):
            raise ValueError("Unable to retrieve token decimals from mirror node")

        decimals = int(token_info.get("decimals"))

        base_amount = to_base_unit(parsed_params.amount, decimals)

        # Normalize scheduling parameters (if present and is_scheduled = True)
        scheduling_params: ScheduleCreateParams | None = None
        if getattr(parsed_params, "scheduling_params", None):
            if parsed_params.scheduling_params.is_scheduled:
                scheduling_params = await HederaParameterNormaliser.normalise_scheduled_transaction_params(
                    parsed_params.scheduling_params, context, client
                )

        return MintFungibleTokenParametersNormalised(
            token_id=TokenId.from_string(parsed_params.token_id),
            amount=int(base_amount),
            scheduling_params=scheduling_params,
        )

    @staticmethod
    async def normalise_create_non_fungible_token_params(
        params: CreateNonFungibleTokenParameters,
        context: Context,
        client: Client,
        mirrornode: IHederaMirrornodeService,
    ) -> CreateNonFungibleTokenParametersNormalised:
        """Normalize parameters for creating a non-fungible token (NFT).

        Args:
            params: The raw input parameters.
            context: The runtime context.
            client: The Hedera client.
            mirrornode: The Mirrornode service instance.

        Returns:
            The normalized parameters are ready for transaction building.
        """
        parsed_params: CreateNonFungibleTokenParameters = cast(
            CreateNonFungibleTokenParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, CreateNonFungibleTokenParameters
            ),
        )

        # Treasury Resolution
        default_account_id = AccountResolver.get_default_account(context, client)
        treasury_account_id = parsed_params.treasury_account_id or default_account_id

        if not treasury_account_id:
            raise ValueError("Must include treasury account ID")

        # Validate max_supply with an INFINITE supply type
        if parsed_params.max_supply is not None and parsed_params.supply_type == 0:
            raise ValueError("Cannot set max supply and INFINITE supply type")

        # Resolve Supply Type
        if parsed_params.supply_type is None:
            supply_type = SupplyType.FINITE  # SPEC DEFAULT
        else:
            if parsed_params.supply_type in (0, SupplyType.INFINITE, "infinite"):
                supply_type = SupplyType.INFINITE
            elif parsed_params.supply_type in (1, SupplyType.FINITE, "finite"):
                supply_type = SupplyType.FINITE
            else:
                raise ValueError("Invalid supply_type; must be finite or infinite.")

        # Resolve Max Supply
        max_supply = None
        if supply_type == SupplyType.FINITE:
            if parsed_params.max_supply is not None:
                max_supply = int(parsed_params.max_supply)
            else:
                max_supply = 100  # Default max supply for FINITE NFTs
        else:
            max_supply = 0  # Python SDK uses 0 to denote infinite supply

        # Supply Key Resolution (MANDATORY for NFTs)
        supply_key: Optional[PublicKey] = None
        public_key_str = None

        # 1. Try to fetch public key from the Treasury Account
        try:
            account_info = await mirrornode.get_account(treasury_account_id)
            if account_info.get("account_public_key"):
                public_key_str = account_info["account_public_key"]
        except Exception:
            pass

        # 2. Fallback to Operator Key if Treasury lookup failed
        if not public_key_str and client.operator_private_key:
            public_key_obj = client.operator_private_key.public_key()
            if public_key_obj:
                public_key_str = public_key_obj.to_string_der()

        # 3. Construct Key or Raise Error
        if public_key_str:
            supply_key = PublicKey.from_string(public_key_str)
        else:
            # Explicitly raise an error as Supply Key is mandatory for NFTs
            raise ValueError(
                "Could not resolve a Supply Key (required for NFTs). Ensure Treasury has a public key or Operator is configured."
            )

        # Construct TokenParams
        token_params = TokenParams(
            token_name=parsed_params.token_name,
            token_symbol=parsed_params.token_symbol,
            decimals=0,  # NFTs have 0 decimals
            initial_supply=0,  # NFTs start with 0 supply
            treasury_account_id=AccountId.from_string(treasury_account_id),
            supply_type=supply_type,
            max_supply=max_supply,
            token_type=TokenType.NON_FUNGIBLE_UNIQUE,
            auto_renew_account_id=AccountId.from_string(default_account_id),
        )

        token_keys = TokenKeys(supply_key=supply_key)

        # Normalize scheduling parameters (if present and is_scheduled = True)
        scheduling_params: ScheduleCreateParams | None = None
        if getattr(parsed_params, "scheduling_params", None):
            if parsed_params.scheduling_params.is_scheduled:
                scheduling_params = await HederaParameterNormaliser.normalise_scheduled_transaction_params(
                    parsed_params.scheduling_params, context, client
                )

        return CreateNonFungibleTokenParametersNormalised(
            token_params=token_params,
            keys=token_keys,
            scheduling_params=scheduling_params,
        )

    @staticmethod
    async def normalise_delete_hbar_allowance(
        params: DeleteHbarAllowanceParameters,
        context: Context,
        client: Client,
    ) -> ApproveHbarAllowanceParametersNormalised:
        """Normalize parameters for deleting an HBAR allowance.

        This function sets the allowance `amount` to **0**, which is the Hedera
        convention for revoking an existing allowance.

        Args:
            params: Raw delete parameters.
            context: Application context.
            client: Hedera client.

        Returns:
            ApproveHbarAllowanceParametersNormalised: Normalized parameters with amount=0.
        """
        parsed_params: DeleteHbarAllowanceParameters = cast(
            DeleteHbarAllowanceParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, DeleteHbarAllowanceParameters
            ),
        )

        owner_id = parsed_params.owner_account_id
        if not owner_id:
            owner_id = AccountResolver.get_default_account(context, client)

        if not owner_id:
            raise ValueError("Owner account ID is required for deleting allowance.")

        spender_id = parsed_params.spender_account_id

        # Create HbarAllowance with amount 0
        allowance = HbarAllowance(
            owner_account_id=AccountId.from_string(owner_id),
            spender_account_id=AccountId.from_string(spender_id),
            amount=0,
        )

        return ApproveHbarAllowanceParametersNormalised(
            hbar_allowances=[allowance],
            transaction_memo=parsed_params.transaction_memo,
        )

    @staticmethod
    async def normalise_approve_token_allowance(
        params: ApproveTokenAllowanceParameters,
        context: Context,
        client: Client,
        mirrornode: IHederaMirrornodeService,
    ) -> ApproveTokenAllowanceParametersNormalised:
        """Normalize parameters for approving token allowances.

        Args:
            params: Raw approval parameters.
            context: Application context.
            client: Hedera client.
            mirrornode: Mirror node service.

        Returns:
            ApproveTokenAllowanceParametersNormalised: Normalized parameters.
        """
        parsed_params: ApproveTokenAllowanceParameters = cast(
            ApproveTokenAllowanceParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, ApproveTokenAllowanceParameters
            ),
        )

        owner_account_id = AccountResolver.resolve_account(
            parsed_params.owner_account_id, context, client
        )

        spender_account_id = parsed_params.spender_account_id

        token_allowances = []
        for token_approval in parsed_params.token_approvals:
            token_info = await mirrornode.get_token_info(token_approval.token_id)
            decimals = int(token_info.get("decimals", 0))

            safe_decimals = decimals if decimals is not None else 0

            base_amount = to_base_unit(token_approval.amount, safe_decimals)

            token_allowances.append(
                TokenAllowance(
                    token_id=TokenId.from_string(token_approval.token_id),
                    owner_account_id=AccountId.from_string(owner_account_id),
                    spender_account_id=AccountId.from_string(spender_account_id),
                    amount=int(base_amount),
                )
            )

        return ApproveTokenAllowanceParametersNormalised(
            token_allowances=token_allowances,
            transaction_memo=parsed_params.transaction_memo,
        )

    @staticmethod
    async def normalise_delete_token_allowance(
        params: DeleteTokenAllowanceParameters,
        context: Context,
        client: Client,
        mirrornode: IHederaMirrornodeService,
    ) -> ApproveTokenAllowanceParametersNormalised:
        """Normalize parameters for deleting token allowances.

        This delegates to `normalise_approve_token_allowance` with the amount set to 0.

        Args:
            params: Raw delete parameters.
            context: Application context.
            client: Hedera client.
            mirrornode: Mirror node service.

        Returns:
            ApproveTokenAllowanceParametersNormalised: Normalized parameters with amount=0.
        """
        parsed_params: DeleteTokenAllowanceParameters = cast(
            DeleteTokenAllowanceParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, DeleteTokenAllowanceParameters
            ),
        )

        # Build approve params with amount = 0 (Hedera convention for revoke)
        # We need to construct the Pydantic model for ApproveTokenAllowanceParameters
        token_approvals = [
            TokenApproval(token_id=token_id, amount=0)
            for token_id in parsed_params.token_ids
        ]

        approve_params = ApproveTokenAllowanceParameters(
            owner_account_id=parsed_params.owner_account_id,
            spender_account_id=parsed_params.spender_account_id,
            token_approvals=token_approvals,
            transaction_memo=parsed_params.transaction_memo,
        )

        return await HederaParameterNormaliser.normalise_approve_token_allowance(
            approve_params, context, client, mirrornode
        )

    @staticmethod
    async def normalise_transfer_fungible_token_with_allowance(
        params: TransferFungibleTokenWithAllowanceParameters,
        context: Context,
        client: Client,
        mirrornode: IHederaMirrornodeService,
    ) -> TransferFungibleTokenWithAllowanceParametersNormalised:
        """Normalize parameters for transferring fungible tokens with allowance.

        Args:
            params: The raw input parameters containing token transfer details including:
                - token_id: ID of the token to transfer
                - source_account_id: Account ID of the token owner
                - transfers: List of transfer entries with recipient account IDs and amounts
                - transaction_memo: Optional memo for the transaction
                - scheduling_params: Optional parameters for scheduled execution
            context: The runtime context for configuration and defaults.
            client: The Hedera client used for transaction execution.
            mirrornode: The Mirrornode service used to fetch token information.

        Returns:
            TransferFungibleTokenWithAllowanceParametersNormalised: Normalized parameters containing:
                - ft_approved_transfer: Dictionary mapping token IDs to account transfer amounts
                - transaction_memo: Optional transaction memo
                - scheduling_params: Optional normalized scheduling parameters

        Raises:
            ValueError: If token decimals cannot be determined or transfer amounts are invalid.
        """
        parsed_params: TransferFungibleTokenWithAllowanceParameters = cast(
            TransferFungibleTokenWithAllowanceParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, TransferFungibleTokenWithAllowanceParameters
            ),
        )

        # Get token info for decimals
        token_info = await mirrornode.get_token_info(parsed_params.token_id)
        if not token_info.get("decimals"):
            raise ValueError("Could not determine token decimals from mirror node.")

        token_decimals = int(token_info["decimals"])

        ft_approved_transfer: dict[TokenId, dict[AccountId, int]] = {}
        token_id = TokenId.from_string(parsed_params.token_id)

        # Initialize the inner dictionary for this token
        ft_approved_transfer[token_id] = {}

        total_amount_base = 0

        # Iterate over the Pydantic models (TokenTransferEntry)
        for transfer in parsed_params.transfers:
            amount_base = int(to_base_unit(transfer.amount, token_decimals))

            if amount_base < 0:
                raise ValueError(f"Invalid transfer amount: {transfer.amount}")

            total_amount_base += amount_base

            recipient_id = AccountId.from_string(transfer.account_id)

            # Add to recipient (credit)
            current_val = ft_approved_transfer[token_id].get(recipient_id, 0)
            ft_approved_transfer[token_id][recipient_id] = current_val + amount_base

        # Add owner deduction (debit)
        owner_id = AccountId.from_string(parsed_params.source_account_id)
        current_owner_val = ft_approved_transfer[token_id].get(owner_id, 0)
        ft_approved_transfer[token_id][owner_id] = current_owner_val - total_amount_base

        # Normalize scheduling parameters (if present and is_scheduled = True)
        scheduling_params: ScheduleCreateParams | None = None
        if getattr(parsed_params, "scheduling_params", None):
            if parsed_params.scheduling_params.is_scheduled:
                scheduling_params = await HederaParameterNormaliser.normalise_scheduled_transaction_params(
                    parsed_params.scheduling_params, context, client
                )

        return TransferFungibleTokenWithAllowanceParametersNormalised(
            ft_approved_transfer=ft_approved_transfer,
            transaction_memo=parsed_params.transaction_memo,
            scheduling_params=scheduling_params,
        )

    @staticmethod
    def normalise_transfer_non_fungible_token_with_allowance(
        params: TransferNonFungibleTokenWithAllowanceParameters,
        context: Context,
    ) -> TransferNonFungibleTokenWithAllowanceParametersNormalised:
        """Normalize parameters for transferring NFTs with allowance.

        Args:
            params: The raw input parameters.
            context: The runtime context.

        Returns:
            The normalized parameters ready for transaction building.
        """
        parsed_params: TransferNonFungibleTokenWithAllowanceParameters = cast(
            TransferNonFungibleTokenWithAllowanceParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, TransferNonFungibleTokenWithAllowanceParameters
            ),
        )

        # Convert token_id to SDK TokenId
        token_id = TokenId.from_string(parsed_params.token_id)
        source_account_id = AccountId.from_string(parsed_params.source_account_id)

        # Map recipients to NftApprovedTransfer objects
        nft_transfers: List[NftApprovedTransferNormalised] = []

        # Note: parsed_params.recipients contains NftApprovedTransferInput objects
        for recipient_input in parsed_params.recipients:
            nft_transfer = NftApprovedTransferNormalised(
                sender_id=source_account_id,
                receiver_id=AccountId.from_string(recipient_input.recipient),
                serial_number=recipient_input.serial_number,
                is_approval=True,
            )
            nft_transfers.append(nft_transfer)

        # Group transfers by token_id (all transfers in this tool call are for the same token)
        nft_approved_transfer = {token_id: nft_transfers}

        return TransferNonFungibleTokenWithAllowanceParametersNormalised(
            nft_approved_transfer=nft_approved_transfer,
            transaction_memo=parsed_params.transaction_memo,
        )
