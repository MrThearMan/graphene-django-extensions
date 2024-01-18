from __future__ import annotations

import datetime
from contextlib import suppress
from enum import Enum
from functools import cached_property, partial
from typing import TYPE_CHECKING

import graphene
from aniso8601 import parse_time
from django.core.exceptions import ValidationError
from django.db import models
from graphene.types.argument import to_arguments
from graphene.types.generic import GenericScalar
from graphene.types.inputobjecttype import InputObjectTypeOptions
from graphene_django.converter import convert_django_field
from graphene_django.filter.fields import convert_enum
from graphene_django.filter.utils import get_filtering_args_from_filterset, get_filterset_class
from graphene_django.utils import maybe_queryset
from query_optimizer import DjangoConnectionField
from query_optimizer.filter import DjangoFilterConnectionField

from ..typing import Operation

if TYPE_CHECKING:
    from django.db.models import Model
    from django_filters import FilterSet
    from graphene.types.argument import Argument
    from graphene.types.unmountedtype import UnmountedType

    from ..bases import DjangoNode
    from ..connections import Connection
    from ..typing import Any, Callable, FieldAliasToLookup, GQLInfo, Self, TypedDict


__all__ = [
    "DjangoFilterConnectionField",
    "DjangoFilterListField",
    "Time",
    "TypedDictField",
    "TypedDictListField",
    "OrderingChoices",
    "UserDefinedFilterInputType",
]


class DjangoFilterConnectionField(DjangoFilterConnectionField):
    # Override this class to support enum ordering in filters.

    @classmethod
    def resolve_queryset(  # noqa: PLR0913
        cls,
        connection: Connection,
        iterable: models.Manager,
        info: GQLInfo,
        args: dict[str, Any],
        filtering_args: dict[str, Any],
        filterset_class: type[FilterSet],
    ) -> models.QuerySet:
        def filter_kwargs() -> dict[str, Any]:
            kwargs = {}
            for k, v in args.items():
                if k in filtering_args:
                    # Remove `order_by` specific checks from here to support `OrderingChoices`.
                    kwargs[k] = convert_enum(v)
            return kwargs

        qs = DjangoConnectionField.resolve_queryset(connection, iterable, info, args)

        filterset = filterset_class(data=filter_kwargs(), queryset=qs, request=info.context)
        if filterset.is_valid():
            return filterset.qs
        raise ValidationError(filterset.form.errors.as_json())  # pragma: no cover


class DjangoFilterListField(graphene.Field):
    def __init__(self, _type: type[DjangoNode], *args: Any, **kwargs: Any) -> None:
        if isinstance(_type, graphene.NonNull):  # pragma: no cover
            _type = _type.of_type
        super().__init__(graphene.List(graphene.NonNull(_type)), *args, **kwargs)

    @staticmethod
    def list_resolver(  # noqa: PLR0913
        node: DjangoNode,
        resolver: Callable,
        manager: models.Manager,
        filtering_args: dict[str, Any],
        filterset_class: type[FilterSet],
        root: Any,
        info: GQLInfo,
        **args: Any,
    ) -> models.QuerySet | None:
        queryset = maybe_queryset(resolver(root, info, **args))
        if queryset is None:  # pragma: no cover
            queryset = maybe_queryset(manager)
        if isinstance(queryset, models.QuerySet):
            queryset = maybe_queryset(node.get_queryset(queryset, info))

        def filter_kwargs() -> dict[str, Any]:  # pragma: no cover
            kwargs: dict[str, Any] = {}
            for k, v in args.items():
                if k in filtering_args:
                    kwargs[k] = convert_enum(v)
            return kwargs

        filterset = filterset_class(data=filter_kwargs(), queryset=queryset, request=info.context)
        if filterset.is_valid():
            return filterset.qs
        raise ValidationError(filterset.form.errors.as_json())  # pragma: no cover

    def wrap_resolve(self, parent_resolver: Callable) -> Callable:
        resolver = super().wrap_resolve(parent_resolver)
        return partial(
            self.list_resolver,
            self.underlying_type,
            resolver,
            self.model._default_manager,
            self.filtering_args,
            self.filterset_class,
        )

    @cached_property
    def underlying_type(self) -> DjangoNode:
        type_ = self.type
        while hasattr(type_, "of_type"):
            type_ = type_.of_type
        return type_

    @property
    def args(self) -> dict[str, Argument]:
        return to_arguments(self._args or {}, self.filtering_args)

    @args.setter
    def args(self, value: dict[str, Argument]) -> None:
        self._args = value

    @cached_property
    def model(self) -> type[models.Model]:
        return self.underlying_type._meta.model

    @cached_property
    def filtering_args(self) -> dict[str, Argument]:
        return get_filtering_args_from_filterset(self.filterset_class, self.underlying_type)

    @cached_property
    def filterset_class(self) -> type[FilterSet]:
        fields = self.underlying_type._meta.filter_fields
        meta = {"model": self.model, "fields": fields}
        filterset_class = self.underlying_type._meta.filterset_class
        return get_filterset_class(filterset_class, **meta)


class Time(graphene.Time):
    """Time scalar that can parse time-strings from database."""

    @staticmethod
    def serialize(time: datetime.time | str) -> str:
        if isinstance(time, str):
            with suppress(ValueError):
                time = parse_time(time)
        return graphene.Time.serialize(time)


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

        enum = Enum(f"{model.__name__}OrderingChoices", fields_map)
        description = f"Ordering fields for the '{model.__name__}' model."

        super().__init_subclass_with_meta__(enum=enum, description=description, **options)


class UserDefinedFilterInputType(graphene.InputObjectType):
    """User defined filtering input."""

    operation = graphene.Field(graphene.Enum.from_enum(Operation), required=True)
    value = GenericScalar()
    operations = graphene.List(graphene.NonNull(lambda: UserDefinedFilterInputType))

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
                    enum=Enum(f"{model.__name__}FilterFields", fields_map),
                    description=f"Filterable fields for the '{model.__name__}' model.",
                ),
            ),
        }

        super().__init_subclass_with_meta__(_meta=_meta, **options)
