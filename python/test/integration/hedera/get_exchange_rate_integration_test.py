import pytest
from hiero_sdk_python import Client

from hedera_agent_kit.plugins.core_misc_query_plugin.get_exchange_rate_tool import (
    get_exchange_rate_query,
)
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.hedera_utils.mirrornode.hedera_mirrornode_utils import (
    get_mirrornode_service,
)
from hedera_agent_kit.shared.parameter_schemas import ExchangeRateQueryParameters
from hedera_agent_kit.shared.utils import ledger_id_from_network


@pytest.fixture(scope="module")
async def setup_client(operator_client):
    yield operator_client


@pytest.mark.asyncio
async def test_fetches_current_exchange_rate(setup_client):
    client: Client = setup_client
    mirrornode = get_mirrornode_service(
        None, ledger_id=ledger_id_from_network(client.network)
    )
    context = Context(
        account_id=str(client.operator_account_id),
        mirrornode_service=mirrornode,
    )

    params = ExchangeRateQueryParameters()

    result = await get_exchange_rate_query(client, context, params)

    assert result is not None
    assert result.extra["exchange_rate"] is not None
    raw = result.extra["exchange_rate"]
    assert "current_rate" in raw
    assert isinstance(raw["current_rate"]["cent_equivalent"], int)
    assert isinstance(raw["current_rate"]["hbar_equivalent"], int)
    assert isinstance(raw["current_rate"]["expiration_time"], int)
    assert isinstance(result.human_message, str)
    assert "Current Rate" in result.human_message
    assert "Next Rate" in result.human_message


@pytest.mark.asyncio
async def test_fetches_exchange_rate_for_specific_timestamp_1(setup_client):
    client: Client = setup_client
    mirrornode = get_mirrornode_service(
        None, ledger_id=ledger_id_from_network(client.network)
    )
    context = Context(
        account_id=str(client.operator_account_id),
        mirrornode_service=mirrornode,
    )

    params = ExchangeRateQueryParameters(timestamp="1726000000")
    result = await get_exchange_rate_query(client, context, params)

    assert result is not None
    raw = result.extra["exchange_rate"]
    assert "current_rate" in raw
    assert isinstance(result.human_message, str)
    assert "Details for timestamp:" in result.human_message
    assert "Current Rate" in result.human_message


@pytest.mark.asyncio
async def test_fetches_exchange_rate_for_specific_timestamp_2(setup_client):
    client: Client = setup_client
    mirrornode = get_mirrornode_service(
        None, ledger_id=ledger_id_from_network(client.network)
    )
    context = Context(
        account_id=str(client.operator_account_id),
        mirrornode_service=mirrornode,
    )

    params = ExchangeRateQueryParameters(timestamp="1757512862.640825000")
    result = await get_exchange_rate_query(client, context, params)

    assert result is not None
    expected = {
        "current_rate": {
            "cent_equivalent": 703411,
            "expiration_time": 1757516400,
            "hbar_equivalent": 30000,
        },
        "next_rate": {
            "cent_equivalent": 707353,
            "expiration_time": 1757520000,
            "hbar_equivalent": 30000,
        },
        "timestamp": "1757512862.640825000",
    }
    assert result.extra["exchange_rate"] == expected


@pytest.mark.asyncio
async def test_handles_invalid_timestamp_input_gracefully(setup_client):
    client: Client = setup_client
    mirrornode = get_mirrornode_service(
        None, ledger_id=ledger_id_from_network(client.network)
    )
    context = Context(
        account_id=str(client.operator_account_id),
        mirrornode_service=mirrornode,
    )

    params = ExchangeRateQueryParameters(timestamp="not-a-timestamp")
    result = await get_exchange_rate_query(client, context, params)

    assert result is not None
    assert isinstance(result.human_message, str)
    assert result.error is not None or "Failed" in result.human_message
