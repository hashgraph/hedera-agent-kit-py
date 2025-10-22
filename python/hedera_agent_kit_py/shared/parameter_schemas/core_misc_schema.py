from typing import Optional, Annotated
from pydantic import Field

from hedera_agent_kit_py.shared.parameter_schemas import BaseModelWithArbitraryTypes


class ExchangeRateQueryParameters(BaseModelWithArbitraryTypes):
    timestamp: Annotated[
        Optional[str],
        Field(
            description="Historical timestamp to query (seconds or nanos since epoch)."
        ),
    ] = None