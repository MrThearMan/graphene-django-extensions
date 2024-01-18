from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework import serializers
from rest_framework.relations import PKOnlyObject

if TYPE_CHECKING:
    from django.db.models import Model


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
