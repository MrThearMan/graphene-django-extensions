from __future__ import annotations

from enum import Enum

__all__ = [
    "Operation",
]


class Operation(Enum):
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
