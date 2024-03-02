from __future__ import annotations

import datetime
from contextlib import suppress
from typing import TYPE_CHECKING

import graphene
import graphql
from aniso8601 import parse_time
from django.db import models
from graphene.types.generic import GenericScalar
from graphene.types.inputobjecttype import InputObjectTypeOptions
from graphene.types.utils import get_field_as
from graphene_django.converter import convert_django_field
from graphql import Undefined
from query_optimizer import DjangoConnectionField, DjangoListField, RelatedField

from ..typing import StrEnum
from ..utils import get_operator_enum

if TYPE_CHECKING:
    from django.db.models import Model
    from graphene.types.unmountedtype import UnmountedType

    from graphene_django_extensions.typing import Any, FieldAliasToLookup, Self, TypedDict


__all__ = [
    "DjangoConnectionField",
    "DjangoListField",
    "Duration",
    "OrderingChoices",
    "RelatedField",
    "Time",
    "TypedDictField",
    "TypedDictListField",
    "UserDefinedFilterInputType",
]


class Time(graphene.Time):
    """Time scalar that can parse time-strings from database."""

    @staticmethod
    def serialize(time: datetime.time | str) -> str:
        if isinstance(time, str):
            with suppress(ValueError):
                time = parse_time(time)
        return graphene.Time.serialize(time)


class Duration(graphene.Scalar):
    """Represents a DurationField value as an integer in seconds."""

    @staticmethod
    def serialize(value: Any) -> int | None:
        if not isinstance(value, datetime.timedelta):  # pragma: no cover
            return None
        return int(value.total_seconds())

    @staticmethod
    def parse_value(value: Any) -> datetime.timedelta | None:
        if not isinstance(value, int):  # pragma: no cover
            return None
        return datetime.timedelta(seconds=value)

    @staticmethod
    def parse_literal(ast: graphql.ValueNode, _variables: Any = None) -> int | Undefined:  # pragma: no cover
        if isinstance(ast, graphql.IntValueNode):
            return int(ast.value)
        return Undefined


class TypedDictFieldMixin:
    CONVERSION_TABLE: dict[type, type[models.Field]] = {
        int: models.IntegerField,
        str: models.CharField,
        bool: models.BooleanField,
        float: models.FloatField,
        dict: models.JSONField,
        list: models.JSONField,
        set: models.JSONField,
        tuple: models.JSONField,
        bytes: models.BinaryField,
        datetime.datetime: models.DateTimeField,
        datetime.date: models.DateField,
        datetime.time: models.TimeField,
    }

    def __init__(self, typed_dict: type[TypedDict], *arg: Any, **kwargs: Any) -> None:  # pragma: no cover
        type_ = self.convert_typed_dict_to_graphene_type(typed_dict)
        super().__init__(type_, *arg, **kwargs)

    def convert_typed_dict_to_graphene_type(self, typed_dict: type[TypedDict]) -> type[graphene.ObjectType]:
        graphene_types: dict[str, UnmountedType] = {}
        for field_name, type_ in typed_dict.__annotations__.items():
            model_field = self.CONVERSION_TABLE.get(type_)
            if model_field is None:
                msg = f"Cannot convert field `{field_name}` of type `{type_.__name__}` to model field."
                raise ValueError(msg)
            graphene_type = convert_django_field(model_field())
            graphene_types[field_name] = graphene_type

        return type(f"{typed_dict.__name__}Type", (graphene.ObjectType,), graphene_types)  # type: ignore[return-value]


class TypedDictField(TypedDictFieldMixin, graphene.Field):
    """Field that converts a TypedDict to a graphene Field ObjectType."""


class TypedDictListField(TypedDictFieldMixin, graphene.List):
    """Field that converts a TypedDict to a graphene List ObjectType."""


class OrderingChoices(graphene.Enum):
    """Get `order_by` choices with Enums rather than strings."""

    @classmethod
    def create(cls, model: type[Model], fields_map: dict[str, str]) -> type[Self]:
        name = f"{model.__name__}OrderingChoices"
        meta_dict = {"model": model, "fields_map": fields_map}
        attrs = {"Meta": type("Meta", (), meta_dict)}
        return type(name, (OrderingChoices,), attrs)

    @classmethod
    def __init_subclass_with_meta__(
        cls,
        model: type[Model] | None = None,
        fields_map: dict[str, str] | None = None,
        **options: Any,
    ) -> None:
        if model is None:  # pragma: no cover
            msg = "'Meta.model' is required."
            raise TypeError(msg)

        if fields_map is None:  # pragma: no cover
            msg = "'Meta.fields' is required."
            raise TypeError(msg)

        enum = StrEnum(f"{model.__name__}OrderingChoices", fields_map)
        description = f"Ordering fields for the '{model.__name__}' model."

        super().__init_subclass_with_meta__(enum=enum, description=description, **options)


class UserDefinedFilterInputType(graphene.InputObjectType):
    """User defined filtering input."""

    operation = graphene.Field(graphene.Enum.from_enum(get_operator_enum()), required=True)
    value = GenericScalar()

    @classmethod
    def create(cls, model: type[Model], fields_map: FieldAliasToLookup) -> type[Self]:
        name = f"{model.__name__}FilterInput"
        meta_dict = {"model": model, "fields_map": fields_map}
        attrs = {"Meta": type("Meta", (), meta_dict)}
        return type(name, (UserDefinedFilterInputType,), attrs)

    @classmethod
    def __init_subclass_with_meta__(
        cls,
        model: type[Model] | None = None,
        fields_map: FieldAliasToLookup | None = None,
        _meta: InputObjectTypeOptions | None = None,
        **options: Any,
    ) -> None:
        if _meta is None:
            _meta = InputObjectTypeOptions(cls)

        if model is None:  # pragma: no cover
            msg = "'Meta.model' is required."
            raise TypeError(msg)

        if fields_map is None:  # pragma: no cover
            msg = "'Meta.fields' is required."
            raise TypeError(msg)

        _meta.fields = {
            "field": graphene.Field(
                graphene.Enum.from_enum(
                    enum=StrEnum(f"{model.__name__}FilterFields", fields_map),
                    description=f"Filterable fields for the '{model.__name__}' model.",
                ),
            ),
            "operations": get_field_as(
                graphene.List(graphene.NonNull(lambda: cls)),
                _as=graphene.InputField,
            ),
        }

        super().__init_subclass_with_meta__(_meta=_meta, **options)
