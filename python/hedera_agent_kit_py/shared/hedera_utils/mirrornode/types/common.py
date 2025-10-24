from typing import TypedDict, Optional


class MirrornodeKeyInfo(TypedDict, total=False):
    description: Optional[str]
    _type: Optional[str]
    example: Optional[str]
    key: Optional[str]


class Links(TypedDict, total=False):
    next: Optional[str]


class TimestampRange(TypedDict, total=False):
    description: Optional[str]
    from_: str  # 'from' is a Python keyword, so we use from_
    to: Optional[str]
