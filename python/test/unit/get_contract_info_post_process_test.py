from hedera_agent_kit_py.plugins.core_evm_query_plugin.get_contract_info_query import (
    post_process,
    get_contract_info_query_prompt,
)


def test_post_process_formats_contract_info():
    sample = {
        "contract_id": "0.0.5005",
        "evm_address": "0xabc123",
        "memo": "Sample contract",
        "deleted": False,
        "created_timestamp": "1700000000.123456789",
        "expiration_timestamp": "1700100000.000000000",
        "admin_key": {"_type": "ED25519", "key": "302a..."},
        "auto_renew_account": "0.0.1001",
        "auto_renew_period": 7776000,
        "max_automatic_token_associations": 10,
        "file_id": "0.0.7007",
        "nonce": 3,
    }

    out = post_process(sample)  # should not raise and should contain formatted lines
    assert "Contract Info Query Result:" in out
    assert "- Contract ID: 0.0.5005" in out
    assert "- EVM Address: 0xabc123" in out
    assert "- Memo: Sample contract" in out
    assert "- Deleted: No" in out
    assert "- Admin Key: 302a..." in out
    assert "- Auto Renew Account: 0.0.1001" in out
    assert "- Auto Renew Period (s): 7776000" in out
    assert "- Max Auto Token Associations: 10" in out
    assert "- Bytecode File ID: 0.0.7007" in out
    assert "- Nonce: 3" in out


def test_prompt_contains_description_and_params():
    prompt = get_contract_info_query_prompt({})
    assert "This tool will return the information for a given Hedera EVM contract" in prompt
    assert "contract_id" in prompt
