from typing import Optional, Annotated

from pydantic import Field

from hedera_agent_kit_py.shared.parameter_schemas import BaseModelWithArbitraryTypes


class TransactionRecordQueryParameters(BaseModelWithArbitraryTypes):
    transaction_id: Annotated[
        str,
        Field(
            description=(
                "The transaction ID to fetch details for. "
                'Should be in format "shard.realm.num-sss-nnn" '
                "where sss are seconds and nnn are nanoseconds"
            ),
        ),
    ]
    nonce: Annotated[
        Optional[int],
        Field(
            ge=0,
            description="Optional nonnegative nonce value for the transaction",
        ),
    ] = None


class TransactionRecordQueryParametersNormalised(TransactionRecordQueryParameters):
    """Normalized form of TransactionRecordQueryParameters. Currently identical."""
