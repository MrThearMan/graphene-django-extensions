from __future__ import annotations

import datetime
from copy import deepcopy
from typing import TYPE_CHECKING

import graphene
from django.db import models
from graphene_django.converter import convert_django_field
from rest_framework.serializers import ListSerializer, ModelSerializer

from .model_operations import get_model_lookup_field

if TYPE_CHECKING:
    from graphene.types.unmountedtype import UnmountedType

    from .typing import FieldNameStr, SerializerMeta, TypedDict


__all__ = [
    "convert_typed_dict_to_graphene_type",
    "convert_serializer_fields_to_not_required",
]


_CONVERSION_TABLE: dict[type, type[models.Field]] = {
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


def convert_typed_dict_to_graphene_type(typed_dict: type[TypedDict]) -> type[graphene.ObjectType]:
    graphene_types: dict[str, UnmountedType] = {}
    for field_name, type_ in typed_dict.__annotations__.items():
        model_field = _CONVERSION_TABLE.get(type_)
        if model_field is None:
            msg = f"Cannot convert field `{field_name}` of type `{type_.__name__}` to model field."
            raise ValueError(msg)
        graphene_type = convert_django_field(model_field())
        graphene_types[field_name] = graphene_type

    return type(f"{typed_dict.__name__}Type", (graphene.ObjectType,), graphene_types)  # type: ignore[return-value]


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
