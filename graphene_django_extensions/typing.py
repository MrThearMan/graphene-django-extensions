from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Literal, Protocol, Sequence, TypeAlias, Union

from django.core.handlers.wsgi import WSGIRequest
from graphql import GraphQLResolveInfo

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser, User
    from django.db.models import Model


__all__ = [
    "Any",
    "AnyUser",
    "GQLInfo",
    "PermCheck",
    "SerializerMeta",
    "RelationType",
]


AnyUser: TypeAlias = Union["User", "AnonymousUser"]
PermCheck: TypeAlias = Callable[["User"], bool] | Callable[["User", "Model"], bool]
RelationType: TypeAlias = Literal["one_to_one", "many_to_one", "one_to_many", "many_to_many"]


class UserHintedWSGIRequest(WSGIRequest):
    user: AnyUser


class GQLInfo(GraphQLResolveInfo):
    context = UserHintedWSGIRequest


class SerializerMeta(Protocol):
    model: type[Model]
    fields: Sequence[str] | Literal["__all__"]
    read_only_fields: Sequence[str] | None
    exclude: Sequence[str] | None
    depth: int | None
    extra_kwargs: dict[str, dict[str, Any]]
