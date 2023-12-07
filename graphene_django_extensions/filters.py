from typing import Any

import django_filters
from django.db import models
from django_filters.constants import EMPTY_VALUES
from django_filters.filterset import FILTER_FOR_DBFIELD_DEFAULTS

from .fields import EnumChoiceField, EnumMultipleChoiceField, IntChoiceField, IntMultipleChoiceField

__all__ = [
    "BaseModelFilterSet",
    "CustomOrderingFilter",
    "IntChoiceFilter",
    "IntMultipleChoiceFilter",
    "EnumChoiceFilter",
    "EnumMultipleChoiceFilter",
]


class IntChoiceFilter(django_filters.TypedChoiceFilter):
    """
    Allow plain integers as choices in GraphQL filters.
    See `IntChoiceField` for motivation.
    """

    field_class = IntChoiceField


class IntMultipleChoiceFilter(django_filters.TypedMultipleChoiceFilter):
    """Same as above but supports multiple choices."""

    field_class = IntMultipleChoiceField


class EnumChoiceFilter(django_filters.TypedChoiceFilter):
    """
    Custom field for handling enums better in GraphQL filters.
    See `EnumChoiceField` for motivation.
    """

    field_class = EnumChoiceField

    def __init__(self, enum: type[models.Choices], *args: Any, **kwargs: Any) -> None:
        kwargs["enum"] = enum
        kwargs["choices"] = enum.choices
        super().__init__(*args, **kwargs)


class EnumMultipleChoiceFilter(django_filters.TypedMultipleChoiceFilter):
    """Same as above but supports multiple choices."""

    field_class = EnumMultipleChoiceField

    def __init__(self, enum: type[models.Choices], *args: Any, **kwargs: Any) -> None:
        kwargs["enum"] = enum
        kwargs["choices"] = enum.choices
        super().__init__(*args, **kwargs)


class BaseModelFilterSet(django_filters.FilterSet):
    FILTER_DEFAULTS = FILTER_FOR_DBFIELD_DEFAULTS
    # Change the default filters for all relationships to not make
    # a database query to check if a corresponding row exists.
    FILTER_DEFAULTS[models.ForeignKey] = {"filter_class": IntChoiceFilter}
    FILTER_DEFAULTS[models.OneToOneField] = {"filter_class": IntChoiceFilter}
    FILTER_DEFAULTS[models.ManyToManyField] = {"filter_class": IntMultipleChoiceFilter}
    FILTER_DEFAULTS[models.OneToOneRel] = {"filter_class": IntChoiceFilter}
    FILTER_DEFAULTS[models.ManyToOneRel] = {"filter_class": IntMultipleChoiceFilter}
    FILTER_DEFAULTS[models.ManyToManyRel] = {"filter_class": IntMultipleChoiceFilter}

    def filter_queryset(self, queryset: models.QuerySet) -> models.QuerySet:
        combination_methods: list[str] = getattr(self.Meta, "combination_methods", [])
        combined_values: dict[str, dict[str, Any]] = {key: {} for key in combination_methods}
        combined_filters: dict[str, django_filters.Filter] = {}

        name: str
        value: Any
        for name, value in self.form.cleaned_data.items():
            field_filter: django_filters.Filter = self.filters[name]
            method: str = field_filter._method  # type: ignore[assignment]
            if method in combination_methods:
                combined_values[method][name] = value
                combined_filters[method] = field_filter
                continue

            queryset = field_filter.filter(queryset, value)
            self._verify_that_queryset(queryset)

        for key, values in combined_values.items():
            queryset = combined_filters[key].filter(queryset, values)
            self._verify_that_queryset(queryset)

        return queryset

    @staticmethod
    def _verify_that_queryset(queryset: Any) -> None:
        if not isinstance(queryset, models.QuerySet):
            msg = f"Expected to receive a QuerySet from filters, but got {type(queryset).__name__} instead."
            raise TypeError(msg)


class CustomOrderingFilter(django_filters.OrderingFilter):
    """Ordering filter for handling custom 'order_by' filters."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.custom_fields: dict[str, str] = self.normalize_fields(kwargs.pop("custom_fields", {}))
        super().__init__(*args, **kwargs)
        self.extra["choices"] += self.build_choices(self.custom_fields, {})

    def filter(self, qs: models.QuerySet, value: list[str]) -> models.QuerySet:  # noqa: A003
        if value in EMPTY_VALUES:
            return qs

        for item in value.copy():
            desc: bool = False
            if item.startswith("-"):
                item = item.removeprefix("-")  # noqa: PLW2901
                desc = True

            if item not in self.custom_fields:
                continue

            value.remove(f"-{item}" if desc else item)
            qs = getattr(self, f"order_by_{item}")(qs, desc=desc)

        return super().filter(qs, value)
