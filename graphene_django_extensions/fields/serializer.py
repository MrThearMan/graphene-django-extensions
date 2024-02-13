from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from rest_framework import serializers
from rest_framework.relations import PKOnlyObject

if TYPE_CHECKING:
    from django.db.models import Model

    from ..typing import Any


__all__ = [
    "IntegerPrimaryKeyField",
    "IntPkOnlyObject",
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


class EnumFriendlyChoiceField(serializers.ChoiceField):  # pragma: no cover
    """ChoiceField that works with enum inputs as well."""

    # TODO: Add tests for this with mutations
    def to_internal_value(self, data: Any) -> str:
        if data == "" and self.allow_blank:
            return ""
        if isinstance(data, Enum):
            data = data.value
        try:
            return self.choice_strings_to_values[str(data)]
        except KeyError:
            self.fail("invalid_choice", input=data)

    def to_representation(self, value: Any) -> Enum:
        if value in ("", None):
            return value
        if isinstance(value, Enum):
            value = value.value
        return self.choice_strings_to_values.get(str(value), value)
