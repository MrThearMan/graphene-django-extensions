from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass

# New in version 3.11
from enum import Enum, StrEnum
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Generic,
    Literal,
    NamedTuple,
    ParamSpec,
    Protocol,
    Self,
    TypeAlias,
    TypedDict,
    TypeVar,
    Union,
)

from django.core.handlers.wsgi import WSGIRequest
from graphene.types.mountedtype import MountedType
from graphene.types.unmountedtype import UnmountedType
from graphql import GraphQLResolveInfo

if TYPE_CHECKING:
    import django_filters
    from django.contrib.auth.models import AnonymousUser, User
    from django.core.exceptions import ValidationError as DjangoValidationError
    from django.db.models import Field, Model, Q, QuerySet
    from django.forms import Form
    from graphql_relay import Edge, PageInfo
    from rest_framework.exceptions import ErrorDetail
    from rest_framework.exceptions import ValidationError as SerializerValidationError
    from rest_framework.serializers import ListSerializer

    from .bases import DjangoNode
    from .constants import Operation
    from .serializers import NestingModelSerializer


__all__ = [
    "Any",
    "AnyUser",
    "Callable",
    "ClassVar",
    "FieldError",
    "FieldNameStr",
    "FilterOverride",
    "FilterSetMeta",
    "GQLFields",
    "GQLInfo",
    "Generic",
    "Iterable",
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
    "SerializerErrorData",
    "SerializerMeta",
    "StrEnum",
    "TypeAlias",
    "TypeVar",
    "TypedDict",
    "Union",
    "ValidationErrorType",
]


FieldNameStr: TypeAlias = str
FieldLookupStr: TypeAlias = str
FilterAliasStr: TypeAlias = str
LookupNameStr: TypeAlias = str
MethodNameStr: TypeAlias = str
AnyUser: TypeAlias = Union["User", "AnonymousUser"]
PermCheck: TypeAlias = Callable[[AnyUser], bool | None] | Callable[[AnyUser, "Model"], bool | None]
RelationType: TypeAlias = Literal["one_to_one", "many_to_one", "one_to_many", "many_to_many"]
RelatedSerializer: TypeAlias = Union["NestingModelSerializer", "ListSerializer"]
Fields: TypeAlias = Sequence[FieldNameStr] | Literal["__all__"]
FieldAliasToLookup: TypeAlias = dict[FilterAliasStr, FieldLookupStr]
FilterFields: TypeAlias = Sequence[FieldLookupStr | tuple[FieldLookupStr, FilterAliasStr]] | Literal["__all__"]
ValidationErrorType: TypeAlias = Union["DjangoValidationError", "SerializerValidationError"]
SerializerErrorData: TypeAlias = dict[str, list[Union["ErrorDetail", str]]]
GQLFields: TypeAlias = dict[str, MountedType | UnmountedType]

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
    fields: Fields
    read_only_fields: Sequence[FieldNameStr]
    exclude: Sequence[FieldNameStr]
    depth: int
    extra_kwargs: Mapping[FieldNameStr, Mapping[str, Any]]
    node: DjangoNode


class FilterSetMeta:
    model: type[Model] | None
    fields: Fields | Mapping[FieldNameStr, Sequence[LookupNameStr]] | None
    exclude: Sequence[FieldNameStr] | None
    filter_overrides: Mapping[Field, FilterOverride]
    form: type[Form]
    combination_methods: Sequence[MethodNameStr]
    order_by: Sequence[FieldNameStr | tuple[FieldLookupStr, FilterAliasStr]]


@dataclass
class UserDefinedFilterInput:
    operation: Operation
    field: Enum | str | None = None
    value: Any = None
    operations: list[UserDefinedFilterInput] | None = None


@dataclass
class UserDefinedFilterResult:
    filters: list[Q]
    annotations: dict[str, Any]
    ordering: list[str]


class FieldError(TypedDict):
    field: str
    message: str
    code: str
