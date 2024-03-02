from __future__ import annotations

from .typing import StrEnum

__all__ = [
    "Operation",
]


class Operation(StrEnum):
    # Logical
    AND = "AND"
    OR = "OR"
    XOR = "XOR"
    NOT = "NOT"

    # Comparison single value
    EXACT = "EXACT"
    IEXACT = "IEXACT"
    GT = "GT"
    GTE = "GTE"
    LT = "LT"
    LTE = "LTE"
    CONTAINS = "CONTAINS"
    ICONTAINS = "ICONTAINS"
    STARTSWITH = "STARTSWITH"
    ISTARTSWITH = "ISTARTSWITH"
    ENDSWITH = "ENDSWITH"
    IENDSWITH = "IENDSWITH"
    ISNULL = "ISNULL"
    REGEX = "REGEX"
    IREGEX = "IREGEX"

    # Comparison multiple values
    IN = "IN"
    RANGE = "RANGE"
