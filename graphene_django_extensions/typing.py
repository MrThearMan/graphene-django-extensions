from __future__ import annotations

import sys
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Literal,
    Mapping,
    NamedTuple,
    ParamSpec,
    Protocol,
    Sequence,
    TypeAlias,
    TypedDict,
    TypeVar,
    Union,
)

# New in version 3.11
if sys.version_info < (3, 11):
    from typing_extensions import Self
else:
    from typing import Self

from django.core.handlers.wsgi import WSGIRequest
from graphql import GraphQLResolveInfo

if TYPE_CHECKING:
    import django_filters
    from django.contrib.auth.models import AnonymousUser, User
    from django.db.models import Field, Model, QuerySet
    from django.forms import Form
    from rest_framework.serializers import ListSerializer

    from .bases import DjangoNode
    from .serializers import BaseModelSerializer


__all__ = [
    "Any",
    "AnyUser",
    "Callable",
    "FieldName",
    "FilterOverride",
    "FilterSetMeta",
    "GQLInfo",
    "Literal",
    "Mapping",
    "NamedTuple",
    "ParamSpec",
    "PermCheck",
    "Protocol",
    "RelatedSerializer",
    "RelationType",
    "Self",
    "Sequence",
    "SerializerMeta",
    "TypeAlias",
    "TypedDict",
    "TypeVar",
    "Union",
]


FieldName: TypeAlias = str
AnyUser: TypeAlias = Union["User", "AnonymousUser"]
PermCheck: TypeAlias = Callable[[AnyUser], bool] | Callable[[AnyUser, "Model"], bool]
RelationType: TypeAlias = Literal["one_to_one", "many_to_one", "one_to_many", "many_to_many"]
RelatedSerializer: TypeAlias = Union["BaseModelSerializer", "ListSerializer"]


class OrderingFunc(Protocol):
    def __call__(self, qs: QuerySet, *, desc: bool) -> QuerySet:
        """Custom ordering function."""


class FilterOverride(TypedDict):
    filter_class: type[django_filters.Filter]
    extra: Callable[[Field], dict[str, Any]]


class UserHintedWSGIRequest(WSGIRequest):
    user: AnyUser


class GQLInfo(GraphQLResolveInfo):
    context = UserHintedWSGIRequest


class SerializerMeta:
    model: type[Model]
    fields: Sequence[str] | Literal["__all__"]
    read_only_fields: Sequence[str]
    exclude: Sequence[str]
    depth: int
    extra_kwargs: dict[str, dict[str, Any]]
    node: DjangoNode


class FilterSetMeta:
    model: type[Model] | None
    fields: Sequence[str] | Mapping[str, Sequence[str]] | None
    exclude: Sequence[str] | None
    filter_overrides: dict[Field, FilterOverride]
    form: type[Form]
    combination_methods: Sequence[str]
    order_by: Sequence[str]
