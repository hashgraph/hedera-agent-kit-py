from typing import Optional, Annotated
from pydantic import BaseModel, Field


class TransactionRecordQueryParameters(BaseModel):
    transaction_id: Annotated[
        str,
        Field(
            ...,
            description=(
                'The transaction ID to fetch details for. '
                'Should be in format "shard.realm.num-sss-nnn" '
                'where sss are seconds and nnn are nanoseconds'
            ),
        ),
    ]
    nonce: Annotated[
        Optional[int],
        Field(
            default=None,
            ge=0,
            description='Optional nonnegative nonce value for the transaction',
        ),
    ]


## TODO: adapt to the Python SDK Transaction Constructor impl
class TransactionRecordQueryParametersNormalised(TransactionRecordQueryParameters):
    """Normalized form of TransactionRecordQueryParameters. Currently identical."""
    pass
