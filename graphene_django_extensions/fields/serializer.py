from __future__ import annotations

import datetime as dt
from enum import Enum
from typing import TYPE_CHECKING

from django.core.validators import MinValueValidator
from rest_framework import serializers
from rest_framework.relations import PKOnlyObject

if TYPE_CHECKING:
    from django.db.models import Model

    from graphene_django_extensions.typing import Any


__all__ = [
    "DurationField",
    "EnumFriendlyChoiceField",
    "IntPkOnlyObject",
    "IntegerPrimaryKeyField",
]


class IntPkOnlyObject(PKOnlyObject):
    """PK object that is coerced to an integer."""

    def __int__(self) -> int:
        return int(self.pk)


class IntegerPrimaryKeyField(serializers.PrimaryKeyRelatedField, serializers.IntegerField):
    """A field that refers to foreign keys by an integer primary key."""

    def get_attribute(self, instance: Model) -> IntPkOnlyObject | None:
        attribute = super().get_attribute(instance)
        if isinstance(attribute, PKOnlyObject) and attribute.pk:
            return IntPkOnlyObject(pk=attribute.pk)
        return None


class EnumFriendlyChoiceField(serializers.ChoiceField):
    """ChoiceField that works with enum inputs as well."""

    def __init__(self, choices: list[tuple[Any, Any]], **kwargs: Any) -> None:
        # Enum can be provided as a keyword argument, used for mutation input enum naming.
        # See: `graphene_django_extensions.converters.convert_serializer_field_to_enum`
        self.enum: Enum | None = kwargs.pop("enum", None)
        super().__init__(choices, **kwargs)

    def to_internal_value(self, data: Any) -> str:
        if data == "" and self.allow_blank:
            return ""
        if isinstance(data, Enum):
            data = data.value
        try:
            return self.choice_strings_to_values[str(data)]
        except KeyError:
            self.fail("invalid_choice", input=data)

    def to_representation(self, value: Any) -> Any:
        if value in ("", None):
            return value
        if isinstance(value, Enum):
            value = value.value
        return self.choice_strings_to_values.get(str(value), value)


class MinDurationValidator(MinValueValidator):
    def clean(self, x: dt.timedelta) -> int:
        return int(x.total_seconds())


class DurationField(serializers.IntegerField):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.validators.append(MinDurationValidator(0))

    def to_internal_value(self, data: Any) -> dt.timedelta:  # type: ignore[override]
        if isinstance(data, dt.timedelta):
            return data
        if isinstance(data, int):
            return dt.timedelta(seconds=data)
        try:
            data = int(data)
        except (ValueError, TypeError):
            self.fail("invalid")
        return dt.timedelta(seconds=data)

    def to_representation(self, value: dt.timedelta) -> int:  # type: ignore[override]
        return int(value.total_seconds())

    def get_attribute(self, instance: Any) -> int | None:
        value = super().get_attribute(instance)
        if isinstance(value, dt.timedelta):
            return int(value.total_seconds())
        return value
