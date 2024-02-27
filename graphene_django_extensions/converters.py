from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

import graphene
from django import forms  # noqa: TCH002
from django.db import models  # noqa: TCH002
from graphene.types.enum import Enum  # noqa: TCH002
from graphene_django.converter import (
    convert_choices_to_named_enum_with_descriptions,
    convert_django_field,
    get_django_field_description,
)
from graphene_django.forms.converter import convert_form_field, get_form_field_description
from graphene_django.registry import Registry  # noqa: TCH002
from graphene_django.rest_framework.serializer_converter import get_graphene_type_from_serializer_field
from rest_framework.fields import ChoiceField  # noqa: TCH002
from rest_framework.serializers import ListSerializer, ModelSerializer

from .fields import (
    Duration,
    DurationField,
    EnumChoiceField,
    EnumMultipleChoiceField,
    IntChoiceField,
    IntMultipleChoiceField,
    OrderByField,
    OrderingChoices,
    Time,
    UserDefinedFilterField,
    UserDefinedFilterInputType,
)
from .model_operations import get_model_lookup_field

if TYPE_CHECKING:
    from django.forms import Field, Form, ModelForm

    from .typing import FieldNameStr, SerializerMeta


__all__ = [
    "convert_form_fields_to_not_required",
    "convert_serializer_fields_to_not_required",
]


def convert_serializer_fields_to_not_required(
    serializer_class: type[ModelSerializer],
    lookup_field: FieldNameStr | None,
    *,
    top_level: bool = True,
) -> type[ModelSerializer | ListSerializer]:
    """
    When updating, usually the wanted behaviour is that the user can only update the
    fields that are actually updated. Therefore, this function can be used to create a new
    serializer class, on which has all the appropriate fields set to `required=False` (except
    the top-level `lookup_field`, which is required to select the row to be updated).
    This function is recursive, so that nested serializers, and their fields are also converted
    to `required=False`.

    :param serializer_class: The serializer class to convert.
    :param lookup_field: The lookup field to be used for the update operation.
    :param top_level: Whether this is the top-level serializer.
    """
    # We need to create a new serializer and rename it since
    # `graphene_django.rest_framework.serializer_converter.convert_serializer_to_input_type`.
    # caches its results by the serializer class name, and thus the input type created for
    # the CREATE operation would be used if created first.
    class_name = f"Update{serializer_class.__name__}"
    new_class: type[ModelSerializer] = type(class_name, (serializer_class,), {})  # type: ignore[assignment]

    # Create a new Meta and deepcopy `extra_kwargs` to avoid changing the original serializer,
    # which might be used for other operations.
    new_class.Meta: SerializerMeta = type("Meta", (serializer_class.Meta,), {})  # type: ignore[assignment]
    new_class.Meta.extra_kwargs = deepcopy(getattr(serializer_class.Meta, "extra_kwargs", {}))

    lookup_field = get_model_lookup_field(new_class.Meta.model, lookup_field)

    for field_name in new_class.Meta.fields:
        _set_extra_kwargs(field_name, new_class.Meta, lookup_field, top_level=top_level)

    # Handle nested serializers
    for field_name, field in new_class._declared_fields.items():
        if isinstance(field, ModelSerializer):
            new_field = convert_serializer_fields_to_not_required(field.__class__, None, top_level=False)
            new_kwargs = field._kwargs | {"required": False}
            new_class._declared_fields[field_name] = new_field(*field._args, **new_kwargs)

        elif isinstance(field, ListSerializer) and isinstance(field.child, ModelSerializer):
            new_child = convert_serializer_fields_to_not_required(field.child.__class__, None, top_level=False)
            new_kwargs = field.child._kwargs | {"required": False, "many": True}
            new_class._declared_fields[field_name] = new_child(*field.child._args, **new_kwargs)

    return new_class


def _set_extra_kwargs(
    field_name: FieldNameStr,
    meta: SerializerMeta,
    lookup_field: FieldNameStr,
    *,
    top_level: bool,
) -> None:
    """Set `meta.extra_kwargs` settings for the given `field_name`."""
    # If the `field_name` is for a model property, should not set anything.
    attr = getattr(meta.model, field_name, None)
    if isinstance(attr, property) and field_name != lookup_field:
        return

    # If the `field_name` is the given `lookup field` while `top_level=True`, should set `required=True`,
    # otherwise should set `required=False`, unless the value has been explicitly set already.
    required = top_level and field_name == lookup_field
    field_options = meta.extra_kwargs.setdefault(field_name, {})
    field_options.setdefault("required", required)

    # Lookup field should be additionally marked as writeable so that
    # serializer doesn't remove it during validation.
    if field_name == lookup_field:
        meta.extra_kwargs.setdefault(field_name, {})["read_only"] = False


def convert_form_fields_to_not_required(form_class: type[ModelForm | Form]) -> type[ModelForm | Form]:
    form_fields: dict[str, Field] = {}
    for field_name, field in form_class.base_fields.items():
        new_field = deepcopy(field)
        new_field.required = False
        form_fields[field_name] = new_field

    return type(form_class.__name__, (form_class,), form_fields)  # type: ignore[return-value]


@convert_django_field.register
def convert_time_to_string(field: models.TimeField, registry: Registry | None = None) -> Time:
    return Time(description=get_django_field_description(field), required=not field.null)


@convert_form_field.register
def convert_form_field_to_time(field: forms.TimeField) -> Time:
    return Time(description=get_form_field_description(field), required=field.required)


@convert_django_field.register
def convert_duration_to_int(field: models.DurationField, registry: Registry | None = None) -> Duration:
    return Duration(description=get_django_field_description(field), required=not field.null)


@convert_form_field.register
def convert_form_field_to_duration(field: forms.DurationField) -> Duration:
    return Duration(description=get_form_field_description(field), required=field.required)


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


@convert_form_field.register
def convert_user_defined_filter(field: UserDefinedFilterField) -> UserDefinedFilterInputType:
    return UserDefinedFilterInputType.create(
        model=field.model,
        fields_map=field.fields_map,
    )(
        description=get_form_field_description(field),
        required=field.required,
    )


@convert_form_field.register
def convert_ordering_field(field: OrderByField) -> graphene.List:
    return graphene.List(
        OrderingChoices.create(model=field.model, fields_map=field.fields_map),
        description=get_form_field_description(field),
        required=field.required,
    )


@get_graphene_type_from_serializer_field.register
def convert_serializer_field_to_duration(field: DurationField) -> type[Duration]:
    return Duration


@get_graphene_type_from_serializer_field.register
def convert_serializer_field_to_enum(field: ChoiceField) -> Enum:
    # `EnumFriendlyChoiceField` can have a reference to the enum class for consistent naming
    # of the same enum in different places (nodes, mutations, filters, etc.)
    if hasattr(field, "enum") and field.enum is not None:  # pragma: no cover
        name = field.enum.__name__
    else:
        name = field.field_name or field.source or "Choices"
        name = "".join(s.capitalize() for s in name.split("_"))
    return convert_choices_to_named_enum_with_descriptions(name, field.choices)
