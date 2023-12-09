from __future__ import annotations

import graphene
from django import forms
from django.db import models  # noqa: TCH002
from graphene_django.converter import convert_django_field, get_django_field_description
from graphene_django.forms.converter import convert_form_field, get_form_field_description
from graphene_django.registry import Registry  # noqa: TCH002
from rest_framework import serializers
from rest_framework.relations import PKOnlyObject

from .typing import TYPE_CHECKING, Any, TypedDict
from .utils import convert_typed_dict_to_graphene_type

if TYPE_CHECKING:
    import datetime


__all__ = [
    "IntegerPrimaryKeyField",
    "IntChoiceField",
    "IntMultipleChoiceField",
    "EnumChoiceField",
    "EnumMultipleChoiceField",
    "TypedDictField",
    "TypedDictListField",
]


class IntPkOnlyObject(PKOnlyObject):
    """PK object that is coerced to an integer."""

    def __int__(self) -> int:
        return int(self.pk)


class IntegerPrimaryKeyField(serializers.PrimaryKeyRelatedField, serializers.IntegerField):
    """A field that refers to foreign keys by an integer primary key."""

    def get_attribute(self, instance: models.Model) -> IntPkOnlyObject | None:
        attribute = super().get_attribute(instance)
        if isinstance(attribute, PKOnlyObject) and attribute.pk:
            return IntPkOnlyObject(pk=attribute.pk)
        return None


class IntChoiceMixin:
    def __init__(self: forms.ChoiceField, **kwargs: Any) -> None:
        kwargs["coerce"] = int
        super().__init__(**kwargs)

    def valid_value(self: forms.ChoiceField, value: Any) -> bool:
        if self.choices:
            return super().valid_value(value)
        try:
            self.coerce(value)
        except (ValueError, TypeError):
            return False
        return True


class IntChoiceField(IntChoiceMixin, forms.TypedChoiceField):
    """Allow plain integers as choices in GraphQL filters. Supports a single choice."""


class IntMultipleChoiceField(IntChoiceMixin, forms.TypedMultipleChoiceField):
    """Same as `IntChoiceField` above but supports multiple choices."""


class EnumChoiceField(forms.ChoiceField):
    """
    Custom field for handling enums better in GraphQL filters. Supports a single choice.
    See `EnumChoiceFilter` for motivation.
    """

    def __init__(self, enum: type[models.Choices], **kwargs: Any) -> None:
        self.enum = enum
        kwargs["choices"] = enum.choices
        super().__init__(**kwargs)


class EnumMultipleChoiceField(forms.MultipleChoiceField):
    """Same as `EnumChoiceField` but supports multiple choices."""

    def __init__(self, enum: type[models.Choices], **kwargs: Any) -> None:
        self.enum = enum
        kwargs["choices"] = enum.choices
        super().__init__(**kwargs)


class TypedDictField(graphene.Field):
    """Field that converts a TypedDict to a graphene Field ObjectType."""

    def __init__(self, typed_dict: type[TypedDict], *arg: Any, **kwargs: Any) -> None:
        type_ = convert_typed_dict_to_graphene_type(typed_dict)
        super().__init__(type_, *arg, **kwargs)


class TypedDictListField(graphene.List):
    """Field that converts a TypedDict to a graphene List ObjectType."""

    def __init__(self, typed_dict: type[TypedDict], *arg: Any, **kwargs: Any) -> None:
        type_ = convert_typed_dict_to_graphene_type(typed_dict)
        super().__init__(type_, *arg, **kwargs)


class Time(graphene.Time):
    """Time scalar that can parse time-strings from database."""

    @staticmethod
    def serialize(time: datetime.time | str) -> str:
        if isinstance(time, str):
            time = Time.parse_value(time)
        return super().serialize(time)


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
