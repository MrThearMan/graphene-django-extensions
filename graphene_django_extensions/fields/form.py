from __future__ import annotations

from typing import TYPE_CHECKING

from django import forms
from graphene.utils.str_converters import to_camel_case

if TYPE_CHECKING:
    from django.db.models import Choices, Model

    from ..typing import Any, FieldAliasToLookup, FieldNameStr

__all__ = [
    "IntChoiceField",
    "IntMultipleChoiceField",
    "EnumChoiceField",
    "EnumMultipleChoiceField",
    "UserDefinedFilterField",
    "OrderByField",
]


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
    def __init__(self, enum: type[Choices], **kwargs: Any) -> None:
        self.enum = enum
        kwargs["choices"] = enum.choices
        super().__init__(**kwargs)


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


class UserDefinedFilterField(forms.Field):
    """Used together with `UserDefinedFilter`."""

    def __init__(self, model: type[Model], fields: FieldAliasToLookup, **kwargs: Any) -> None:
        self.model = model
        self.fields_map = fields
        super().__init__(**kwargs)


class OrderByField(forms.Field):
    """Used together with `CustomOrderingFilter`."""

    def __init__(self, model: type[Model], choices: list[tuple[FieldNameStr, str]], **kwargs: Any) -> None:
        self.model = model
        self.fields_map: dict[str, str] = {
            to_camel_case(name[1:]) + "Desc" if name[0] == "-" else to_camel_case(name) + "Asc": name
            for name, _ in choices
        }
        kwargs.pop("null_label", None)
        super().__init__(**kwargs)
