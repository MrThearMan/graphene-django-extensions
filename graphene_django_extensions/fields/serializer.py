from __future__ import annotations

import datetime
from enum import Enum
from typing import TYPE_CHECKING

from django.core.validators import MinValueValidator
from rest_framework import serializers
from rest_framework.relations import PKOnlyObject

if TYPE_CHECKING:
    from django.db.models import Model

    from ..typing import Any


__all__ = [
    "IntegerPrimaryKeyField",
    "IntPkOnlyObject",
    "DurationField",
    "EnumFriendlyChoiceField",
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
        return None  # pragma: no cover


class EnumFriendlyChoiceField(serializers.ChoiceField):
    """ChoiceField that works with enum inputs as well."""

    def __init__(self, choices: list[tuple[Any, Any]], **kwargs: Any) -> None:
        # Enum can be provided as a keyword argument, used for mutation input enum naming.
        # See: `graphene_django_extensions.converters.convert_serializer_field_to_enum`
        self.enum: Enum | None = kwargs.pop("enum", None)
        super().__init__(choices, **kwargs)

    def to_internal_value(self, data: Any) -> str:
        if data == "" and self.allow_blank:  # pragma: no cover
            return ""
        if isinstance(data, Enum):  # pragma: no cover
            data = data.value
        try:
            return self.choice_strings_to_values[str(data)]
        except KeyError:  # pragma: no cover
            self.fail("invalid_choice", input=data)

    def to_representation(self, value: Any) -> Enum:  # pragma: no cover
        if value in ("", None):
            return value
        if isinstance(value, Enum):
            value = value.value
        return self.choice_strings_to_values.get(str(value), value)


class MinDurationValidator(MinValueValidator):
    def clean(self, x: datetime.timedelta) -> int:
        return int(x.total_seconds())


class DurationField(serializers.IntegerField):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.validators.append(MinDurationValidator(0))

    def to_internal_value(self, data: Any) -> datetime.timedelta:
        if isinstance(data, datetime.timedelta):
            return data
        if isinstance(data, int):
            return datetime.timedelta(seconds=data)
        try:  # pragma: no cover
            data = int(data)
        except (ValueError, TypeError):  # pragma: no cover
            self.fail("invalid")
        return datetime.timedelta(seconds=data)  # pragma: no cover

    def to_representation(self, value: datetime.timedelta) -> int:  # pragma: no cover
        return int(value.total_seconds())

    def get_attribute(self, instance: Any) -> int | None:
        value = super().get_attribute(instance)
        if isinstance(value, datetime.timedelta):
            return int(value.total_seconds())
        return value  # pragma: no cover
