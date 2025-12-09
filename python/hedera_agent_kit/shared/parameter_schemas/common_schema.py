from typing import Optional, Union, Annotated

from hiero_sdk_python.schedule.schedule_create_transaction import ScheduleCreateParams
from pydantic import BaseModel, Field


class BaseModelWithArbitraryTypes(BaseModel):
    model_config = {"arbitrary_types_allowed": True}


class SchedulingParams(BaseModelWithArbitraryTypes):
    """Optional scheduling parameters for transactions."""

    is_scheduled: Annotated[
        bool, Field(description="Set to true when user asks for scheduling, executing later a transaction or creating a scheduled transaction")
    ] = False

    admin_key: Annotated[
        Union[bool, str],
        Field(
            description=(
                "Admin key that can delete or modify the scheduled transaction before execution. "
                "If true, the operator key will be used. If false or omitted, no admin key is set. "
                "If a string is passed, it will be used as the admin key."
            ),
        ),
    ] = False

    payer_account_id: Annotated[
        Optional[str],
        Field(
            description=(
                "Account that will pay the transaction fee when the scheduled transaction executes. "
                "Defaults to the operator account if omitted."
            ),
        ),
    ] = None

    expiration_time: Annotated[
        Optional[str],
        Field(
            description="Time when the scheduled transaction will expire if not fully signed (ISO 8601 format).",
        ),
    ] = None

    wait_for_expiry: Annotated[
        bool,
        Field(
            description=(
                "If true, the scheduled transaction will be executed at its expiration time, "
                "regardless of when all required signatures are collected. "
                "If false, it executes as soon as all required signatures are present. "
                "Requires expiration_time to be set."
            ),
        ),
    ] = False


class OptionalScheduledTransactionParams(BaseModelWithArbitraryTypes):
    """Wrapper model containing optional scheduling parameters."""

    scheduling_params: Annotated[
        Optional[SchedulingParams],
        Field(
            description=(
                "Optional scheduling parameters. Used to control whether the transaction should be scheduled, "
                "provide metadata, control payer/admin keys, and manage execution/expiration behavior."
            ),
        ),
    ] = None


class OptionalScheduledTransactionParamsNormalised(BaseModelWithArbitraryTypes):
    scheduling_params: Optional[ScheduleCreateParams] = None
    """Wrapper model for normalised scheduling parameters."""
