import pytest
from unittest.mock import AsyncMock, patch

from hiero_sdk_python import Network

from hedera_agent_kit_py.plugins.core_evm_query_plugin.get_contract_info_query import (
    post_process,
    _format_timestamp,
    _format_key,
    get_contract_info_query,
)
from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.parameter_schemas.evm_schema import (
    ContractInfoQueryParameters,
)


def test_post_process_with_full_data():
    contract = {
        "contract_id": "0.0.5005",
        "evm_address": "0xabcdef0123456789abcdef0123456789abcdef01",
        "memo": "Sample contract",
        "deleted": False,
        "created_timestamp": "1700000000.123456789",
        "expiration_timestamp": "1800000000.987654321",
        "admin_key": {"_type": "ed25519", "key": "0xABCDEF"},
        "auto_renew_account": "0.0.9999",
        "auto_renew_period": 7776000,
        "max_automatic_token_associations": 10,
        "file_id": "0.0.6006",
        "nonce": 3,
    }

    expected = (
        "Contract Info Query Result:\n"
        f"- Contract ID: {contract['contract_id']}\n"
        f"- EVM Address: {contract['evm_address']}\n"
        f"- Memo: {contract['memo']}\n"
        f"- Deleted: No\n"
        f"- Created: {_format_timestamp(contract['created_timestamp'])}\n"
        f"- Expiration: {_format_timestamp(contract['expiration_timestamp'])}\n"
        f"- Admin Key: {_format_key(contract['admin_key'])}\n"
        f"- Auto Renew Account: {contract['auto_renew_account']}\n"
        f"- Auto Renew Period (s): {contract['auto_renew_period']}\n"
        f"- Max Auto Token Associations: {contract['max_automatic_token_associations']}\n"
        f"- Bytecode File ID: {contract['file_id']}\n"
        f"- Nonce: {contract['nonce']}"
    )

    assert post_process(contract) == expected


def test_post_process_with_missing_data_uses_defaults():
    contract = {
        # Intentionally minimal; rely on defaults in post_process
        "contract_id": "0.0.123",
        # leave other fields absent
    }

    result = post_process(contract)

    assert "- Contract ID: 0.0.123" in result
    assert "- EVM Address: N/A" in result
    assert "- Memo: N/A" in result
    # deleted is missing -> No
    assert "- Deleted: No" in result
    # timestamps missing -> N/A
    assert "- Created: N/A" in result
    assert "- Expiration: N/A" in result
    # admin key missing -> Not Set
    assert "- Admin Key: Not Set" in result
    assert "- Auto Renew Account: N/A" in result
    assert "- Auto Renew Period (s): N/A" in result
    assert "- Max Auto Token Associations: N/A" in result
    assert "- Bytecode File ID: N/A" in result
    assert "- Nonce: N/A" in result


@pytest.mark.asyncio
@patch(
    "hedera_agent_kit_py.plugins.core_evm_query_plugin.get_contract_info_query.get_mirrornode_service"
)
async def test_get_contract_info_query_returns_expected_output(mock_get_service):
    # Arrange mock mirrornode service
    mock_service = AsyncMock()
    info = {
        "contract_id": "0.0.42",
        "evm_address": "0x42",
        "memo": "Meaning of life",
        "deleted": True,
        "created_timestamp": "1700000100.0",
        "expiration_timestamp": None,
        "admin_key": None,
        "auto_renew_account": None,
        "auto_renew_period": None,
        "max_automatic_token_associations": None,
        "file_id": "0.0.7",
        "nonce": None,
    }
    mock_service.get_contract_info = AsyncMock(return_value=info)
    mock_get_service.return_value = mock_service

    # Fake client and context
    class FakeClient:
        def __init__(self):
            self.network = Network(network="testnet")

    client = FakeClient()
    context = Context()
    params = {"contract_id": "0.0.42"}

    # Act
    response = await get_contract_info_query(client, context, params)

    # Assert
    assert response.error is None
    assert response.human_message == post_process(info)
