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
    Union,
)

from graphene.types.mountedtype import MountedType
from graphene.types.unmountedtype import UnmountedType
from query_optimizer.typing import GQLInfo, TModel, TUser, UserHintedWSGIRequest

# Type parameter defaults are new in Python 3.13.
from typing_extensions import TypeVar

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
    "TData",
    "TModel",
    "TUser",
    "TypeAlias",
    "TypeVar",
    "TypedDict",
    "Union",
    "UserHintedWSGIRequest",
    "ValidationErrorType",
]


type FieldNameStr = str
type FieldLookupStr = str
type FilterAliasStr = str
type LookupNameStr = str
type MethodNameStr = str
type AnyUser = User | AnonymousUser
type PermCheck = Callable[[AnyUser], bool | None] | Callable[[AnyUser, Model], bool | None]
type RelationType = Literal["one_to_one", "many_to_one", "one_to_many", "many_to_many"]
type RelatedSerializer = NestingModelSerializer | ListSerializer
type Fields = Sequence[FieldNameStr] | Literal["__all__"]
type FieldAliasToLookup = dict[FilterAliasStr, FieldLookupStr]
type FilterFields = Sequence[FieldLookupStr | tuple[FieldLookupStr, FilterAliasStr]] | Literal["__all__"]
type ValidationErrorType = DjangoValidationError | SerializerValidationError
type SerializerErrorData = dict[str, list[ErrorDetail | str]]
type GQLFields = dict[str, MountedType | UnmountedType]

# Subscribe the generic base classes with these and 'TModel' and 'TUser' to type their hooks
# for a specific model, user or validated data. Without subscription, the defaults apply.
TData = TypeVar("TData", bound=Mapping[str, Any], default=dict[str, Any])


class NodeConnectionType[T: Model](Protocol):
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
