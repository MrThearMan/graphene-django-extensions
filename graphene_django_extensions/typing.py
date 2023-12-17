from __future__ import annotations

import sys
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
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
if sys.version_info < (3, 11):  # pragma: no cover
    from typing_extensions import Self
else:  # pragma: no cover
    from typing import Self

from django.core.handlers.wsgi import WSGIRequest
from graphql import GraphQLResolveInfo

if TYPE_CHECKING:
    import django_filters
    from django.contrib.auth.models import AnonymousUser, User
    from django.db.models import Field, Model, QuerySet
    from django.forms import Form
    from graphql_relay import Edge, PageInfo
    from rest_framework.serializers import ListSerializer

    from .bases import DjangoNode
    from .serializers import NestingModelSerializer


__all__ = [
    "Any",
    "AnyUser",
    "Callable",
    "FieldNameStr",
    "FilterOverride",
    "FilterSetMeta",
    "Generic",
    "GQLInfo",
    "Literal",
    "Mapping",
    "NamedTuple",
    "NodeConnectionType",
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


FieldNameStr: TypeAlias = str
FieldLookupStr: TypeAlias = str
FilterAliasStr: TypeAlias = str
LookupNameStr: TypeAlias = str
MethodNameStr: TypeAlias = str
AnyUser: TypeAlias = Union["User", "AnonymousUser"]
PermCheck: TypeAlias = Callable[[AnyUser], bool] | Callable[[AnyUser, "Model"], bool]
RelationType: TypeAlias = Literal["one_to_one", "many_to_one", "one_to_many", "many_to_many"]
RelatedSerializer: TypeAlias = Union["NestingModelSerializer", "ListSerializer"]

T = TypeVar("T")


class NodeConnectionType(Protocol[T]):
    page_info: PageInfo
    edged: list[Edge]
    iterable: QuerySet[T]
    length: int


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
    fields: Sequence[FieldNameStr] | Literal["__all__"]
    read_only_fields: Sequence[FieldNameStr]
    exclude: Sequence[FieldNameStr]
    depth: int
    extra_kwargs: Mapping[FieldNameStr, Mapping[str, Any]]
    node: DjangoNode


class FilterSetMeta:
    model: type[Model] | None
    fields: Sequence[FieldNameStr] | Mapping[FieldNameStr, Sequence[LookupNameStr]] | Literal["__all__"] | None
    exclude: Sequence[FieldNameStr] | None
    filter_overrides: Mapping[Field, FilterOverride]
    form: type[Form]
    combination_methods: Sequence[MethodNameStr]
    order_by: Sequence[FieldLookupStr | tuple[FieldLookupStr, FilterAliasStr]]
