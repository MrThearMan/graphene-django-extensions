from __future__ import annotations

from typing import TYPE_CHECKING

import graphene

if TYPE_CHECKING:
    from .typing import Any, GQLInfo, NodeConnectionType

__all__ = [
    "Connection",
]


class Connection(graphene.Connection):
    """Connection field that adds the `totalCount` field to the connection."""

    class Meta:
        abstract = True

    total_count = graphene.Int()

    def resolve_total_count(root: NodeConnectionType, info: GQLInfo, **kwargs: Any) -> int:  # noqa: N805
        return root.length
