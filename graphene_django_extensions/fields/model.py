from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

if TYPE_CHECKING:
    from django.forms import Field

    from graphene_django_extensions.typing import Any, Sequence

__all__ = [
    "IntChoiceField",
    "StrChoiceField",
]


class StrChoiceField(models.CharField):  # pragma: no cover
    """CharField for TextChoices that automatically sets 'max_length' to the length of the longest choice."""

    def __init__(self, enum: type[models.Choices], **kwargs: Any) -> None:
        self.enum = enum
        kwargs["max_length"] = max(len(val) for val, _ in enum.choices)
        kwargs["choices"] = enum.choices
        super().__init__(**kwargs)

    def deconstruct(self) -> tuple[str, str, Sequence[Any], dict[str, Any]]:
        name, path, args, kwargs = super().deconstruct()
        kwargs["enum"] = self.enum
        return name, path, args, kwargs


class IntChoiceField(models.IntegerField):  # pragma: no cover
    """
    IntegerField for IntegerChoices that sets 'min_value' and 'max_value' validators
    instead of regular choice validation. Useful when you don't want integer choices to be
    converted to strings in graphql endpoints (ref: `graphene_django.converter.convert_choice_name`).
    Pair with `IntChoiceField` to validate choices in serializers.
    """

    def __init__(self, enum: type[models.Choices], **kwargs: Any) -> None:
        self.enum = enum

        min_value = int(min(val for val, _ in enum.choices))
        max_value = int(max(val for val, _ in enum.choices))
        msg = f"Value must be between {min_value} and {max_value}."
        # These validators are passed to the serializer field as its 'min_value' and 'max_value'.
        kwargs["validators"] = [
            MinValueValidator(limit_value=min_value, message=msg),
            MaxValueValidator(limit_value=max_value, message=msg),
        ]
        super().__init__(**kwargs)

    def deconstruct(self) -> tuple[str, str, Sequence[Any], dict[str, Any]]:
        name, path, args, kwargs = super().deconstruct()
        kwargs["enum"] = self.enum
        return name, path, args, kwargs

    def validate(self, value: int | None, model_instance: Any) -> None:
        original_choices = self.choices
        try:
            self.choices = self.enum.choices
            super().validate(value, model_instance)
        finally:
            self.choices = original_choices

    def formfield(self, **kwargs: Any) -> Field:
        original_choices = self.choices
        try:
            self.choices = self.enum.choices
            choices = super().formfield(**kwargs)
        finally:
            self.choices = original_choices

        return choices
