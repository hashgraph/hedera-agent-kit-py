from typing import Optional, Union, Annotated

from hiero_sdk_python.schedule.schedule_create_transaction import ScheduleCreateParams
from pydantic import BaseModel, Field
from hiero_sdk_python import AccountId, PublicKey, Timestamp


class SchedulingParams(BaseModel):
    """Optional scheduling parameters for transactions."""

    is_scheduled: Annotated[
        Optional[bool],
        Field(
            default=False,
            description=(
                "If true, the transaction will be created as a scheduled transaction. "
                "If false or omitted, all other scheduling parameters will be ignored."
            ),
        ),
    ]

    admin_key: Annotated[
        Optional[Union[bool, str]],
        Field(
            default=False,
            description=(
                "Admin key that can delete or modify the scheduled transaction before execution. "
                "If true, the operator key will be used. If false or omitted, no admin key is set. "
                "If a string is passed, it will be used as the admin key."
            ),
        ),
    ]

    payer_account_id: Annotated[
        Optional[str],
        Field(
            default=None,
            description=(
                "Account that will pay the transaction fee when the scheduled transaction executes. "
                "Defaults to the operator account if omitted."
            ),
        ),
    ]

    expiration_time: Annotated[
        Optional[str],
        Field(
            default=None,
            description="Time when the scheduled transaction will expire if not fully signed (ISO 8601 format).",
        ),
    ]

    wait_for_expiry: Annotated[
        Optional[bool],
        Field(
            default=False,
            description=(
                "If true, the scheduled transaction will be executed at its expiration time, "
                "regardless of when all required signatures are collected. "
                "If false, it executes as soon as all required signatures are present. "
                "Requires expiration_time to be set."
            ),
        ),
    ]


class OptionalScheduledTransactionParams(BaseModel):
    """Wrapper model containing optional scheduling parameters."""

    scheduling_params: Annotated[
        Optional[SchedulingParams],
        Field(
            default=None,
            description=(
                "Optional scheduling parameters. Used to control whether the transaction should be scheduled, "
                "provide metadata, control payer/admin keys, and manage execution/expiration behavior."
            ),
        ),
    ]

## TODO: adapt to the Python SDK Transaction Constructor impl
class OptionalScheduledTransactionParamsNormalised(ScheduleCreateParams):
    """Wrapper model for normalised scheduling parameters."""