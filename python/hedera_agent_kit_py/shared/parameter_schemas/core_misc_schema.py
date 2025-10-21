from typing import Optional, Annotated
from pydantic import BaseModel, Field


class ExchangeRateQueryParameters(BaseModel):
    timestamp: Annotated[
        Optional[str],
        Field(
            default=None,
            description="Historical timestamp to query (seconds or nanos since epoch)."
        ),
    ]