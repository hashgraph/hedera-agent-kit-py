from hiero_sdk_python.schedule.schedule_id import ScheduleId

from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.parameter_schemas.account_schema import (
    ScheduleDeleteTransactionParameters,
)


class TestScheduleDeleteParameterNormalization:
    def test_normalises_valid_schedule_id(self):
        params = ScheduleDeleteTransactionParameters(schedule_id="0.0.123456")

        res = HederaParameterNormaliser.normalise_schedule_delete_transaction(params)

        assert isinstance(res.schedule_id, ScheduleId)
        assert str(res.schedule_id) == "0.0.123456"
