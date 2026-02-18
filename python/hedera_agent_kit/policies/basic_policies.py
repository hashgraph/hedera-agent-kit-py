from typing import List


from ..shared.configuration import Context
from ..shared.policy import Policy
from ..shared.abstract_hook import PostParamsNormalizationParams


class RequiredAccountMemoPolicy(Policy):
    def __init__(self, relevant_tools: List[str] = None):
        self._relevant_tools = relevant_tools or []
        self._description = "Account memo is required."

    @property
    def name(self) -> str:
        return "RequiredAccountMemoPolicy"

    @property
    def description(self) -> str:
        return self._description

    @property
    def relevant_tools(self) -> List[str]:
        return self._relevant_tools

    async def should_block_post_params_normalization(
        self, context: Context, params: PostParamsNormalizationParams
    ) -> bool:
        memo = getattr(params.normalized_params, "account_memo", None)
        if not memo:
            return True
        else:
            return False
