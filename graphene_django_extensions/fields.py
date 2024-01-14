from __future__ import annotations

from contextlib import suppress
from enum import Enum
from typing import TYPE_CHECKING

import graphene
from aniso8601 import parse_time
from django import forms
from django.core.exceptions import ValidationError
from django.db import models
from graphene.types.generic import GenericScalar
from graphene.types.inputobjecttype import InputObjectTypeOptions
from graphene.utils.str_converters import to_camel_case
from graphene_django.converter import convert_django_field, get_django_field_description
from graphene_django.filter.fields import convert_enum
from graphene_django.forms.converter import convert_form_field, get_form_field_description
from graphene_django.registry import Registry  # noqa: TCH002
from query_optimizer import DjangoConnectionField
from query_optimizer.filter import DjangoFilterConnectionField
from rest_framework import serializers
from rest_framework.relations import PKOnlyObject

from .converters import convert_typed_dict_to_graphene_type
from .typing import Operation

if TYPE_CHECKING:
    import datetime

    from django.db.models import Model
    from django_filters import FilterSet
    from graphene_django import DjangoListField

    from .bases import DjangoNode
    from .connections import Connection
    from .typing import Any, FieldAliasToLookup, GQLInfo, Self, TypedDict


__all__ = [
    "IntegerPrimaryKeyField",
    "IntChoiceField",
    "IntMultipleChoiceField",
    "EnumChoiceField",
    "EnumMultipleChoiceField",
    "TypedDictField",
    "TypedDictListField",
]


class DjangoFilterConnectionField(DjangoFilterConnectionField):
    """Override this class to support enum ordering in filters."""

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
                    # Remove `order_by` specific checks from here.
                    # Custom `order_by` filter makes them enums,
                    # so they should still be converted to strings.
                    kwargs[k] = convert_enum(v)
            return kwargs

        qs = DjangoConnectionField.resolve_queryset(connection, iterable, info, args)

        filterset = filterset_class(data=filter_kwargs(), queryset=qs, request=info.context)
        if filterset.is_valid():
            return filterset.qs
        raise ValidationError(filterset.form.errors.as_json())  # pragma: no cover


class IntPkOnlyObject(PKOnlyObject):
    """PK object that is coerced to an integer."""

    def __int__(self) -> int:
        return int(self.pk)


class IntChoiceFieldMixin:
    def __init__(self: forms.TypedChoiceField | forms.TypedMultipleChoiceField, **kwargs: Any) -> None:
        kwargs["coerce"] = int
        kwargs["empty_value"] = None
        super().__init__(**kwargs)

    def valid_value(self: forms.TypedChoiceField | forms.TypedMultipleChoiceField, value: Any) -> bool:
        if self.choices:  # pragma: no cover
            parent: forms.TypedChoiceField = super()  # type: ignore[assignment]
            return parent.valid_value(value)
        try:
            self.coerce(value)
        except (ValueError, TypeError):  # pragma: no cover
            return False
        return True


class EnumChoiceFieldMixin:
    def __init__(self, enum: type[models.Choices], **kwargs: Any) -> None:
        self.enum = enum
        kwargs["choices"] = enum.choices
        super().__init__(**kwargs)


class TypedDictFieldMixin:
    def __init__(self, typed_dict: type[TypedDict], *arg: Any, **kwargs: Any) -> None:  # pragma: no cover
        type_ = convert_typed_dict_to_graphene_type(typed_dict)
        super().__init__(type_, *arg, **kwargs)


class IntegerPrimaryKeyField(serializers.PrimaryKeyRelatedField, serializers.IntegerField):
    """A field that refers to foreign keys by an integer primary key."""

    def get_attribute(self, instance: models.Model) -> IntPkOnlyObject | None:
        attribute = super().get_attribute(instance)
        if isinstance(attribute, PKOnlyObject) and attribute.pk:
            return IntPkOnlyObject(pk=attribute.pk)
        return None  # pragma: no cover


class IntChoiceField(IntChoiceFieldMixin, forms.TypedChoiceField):
    """Allow plain integers as choices in GraphQL filters. Supports a single choice."""


class IntMultipleChoiceField(IntChoiceFieldMixin, forms.TypedMultipleChoiceField):
    """Same as `IntChoiceField` above but supports multiple choices."""


class EnumChoiceField(EnumChoiceFieldMixin, forms.ChoiceField):
    """
    Custom field for handling enums better in GraphQL filters. Supports a single choice.
    See `EnumChoiceFilter` for motivation.
    """


class EnumMultipleChoiceField(EnumChoiceFieldMixin, forms.MultipleChoiceField):
    """Same as `EnumChoiceField` but supports multiple choices."""


class TypedDictField(TypedDictFieldMixin, graphene.Field):
    """Field that converts a TypedDict to a graphene Field ObjectType."""


class TypedDictListField(TypedDictFieldMixin, graphene.List):
    """Field that converts a TypedDict to a graphene List ObjectType."""


class Time(graphene.Time):
    """Time scalar that can parse time-strings from database."""

    @staticmethod
    def serialize(time: datetime.time | str) -> str:
        if isinstance(time, str):
            with suppress(ValueError):
                time = parse_time(time)
        return graphene.Time.serialize(time)


@convert_django_field.register
def convert_time_to_string(field: models.TimeField, registry: Registry | None = None) -> Time:
    return Time(description=get_django_field_description(field), required=not field.null)


@convert_form_field.register
def convert_form_field_to_time(field: forms.TimeField) -> Time:
    return Time(description=get_form_field_description(field), required=field.required)


@convert_form_field.register
def convert_form_field_to_int(field: IntChoiceField) -> graphene.Int:
    return graphene.Int(description=get_form_field_description(field), required=field.required)


@convert_form_field.register
def convert_form_field_to_list_of_int(field: IntMultipleChoiceField) -> graphene.List:
    return graphene.List(graphene.Int, description=get_form_field_description(field), required=field.required)


@convert_form_field.register
def convert_form_field_to_enum(field: EnumChoiceField) -> graphene.Enum:
    return graphene.Enum.from_enum(field.enum)(
        description=get_form_field_description(field),
        required=field.required,
    )


@convert_form_field.register
def convert_form_field_to_enum_list(field: EnumMultipleChoiceField) -> graphene.List:
    return graphene.List(
        graphene.Enum.from_enum(field.enum),
        description=get_form_field_description(field),
        required=field.required,
    )


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


class UserDefinedFilterField(forms.Field):
    def __init__(self, model: type[Model], fields: FieldAliasToLookup, **kwargs: Any) -> None:
        self.model = model
        self.fields_map = fields
        super().__init__(**kwargs)


@convert_form_field.register
def convert_user_defined_filter(field: UserDefinedFilterField) -> UserDefinedFilterInputType:
    return UserDefinedFilterInputType.create(
        model=field.model,
        fields_map=field.fields_map,
    )(
        description=get_form_field_description(field),
        required=field.required,
    )


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


class OrderByField(forms.Field):
    def __init__(self, model: type[Model], choices: list[tuple[str, str]], **kwargs: Any) -> None:
        self.model = model
        self.fields_map: dict[str, str] = {
            to_camel_case(name[1:]) + "Desc" if name[0] == "-" else to_camel_case(name) + "Asc": name
            for name, _ in choices
        }
        kwargs.pop("null_label", None)
        super().__init__(**kwargs)


@convert_form_field.register
def convert_ordering_field(field: OrderByField) -> graphene.List:
    return graphene.List(
        OrderingChoices.create(model=field.model, fields_map=field.fields_map),
        description=get_form_field_description(field),
        required=field.required,
    )


@convert_django_field.register(models.ManyToManyField)
@convert_django_field.register(models.ManyToManyRel)
@convert_django_field.register(models.ManyToOneRel)
def convert_to_many_field_to_list_or_connection(
    field,  # noqa: ANN001
    registry: Registry | None = None,
) -> graphene.Dynamic:
    def dynamic_type() -> DjangoFilterConnectionField | DjangoConnectionField | DjangoListField | None:
        _type: DjangoNode | None = registry.get_type_for_model(field.related_model)
        if _type is None:  # pragma: no cover
            return None

        if _type._meta.connection:
            return _type.Connection()
        return _type.ListField()  # pragma: no cover

    return graphene.Dynamic(dynamic_type)
