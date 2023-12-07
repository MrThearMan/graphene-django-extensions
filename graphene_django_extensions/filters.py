from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

import django_filters
from django.db import models
from django_filters.constants import EMPTY_VALUES
from django_filters.filterset import FILTER_FOR_DBFIELD_DEFAULTS

from .fields import (
    EnumChoiceField,
    EnumChoiceFilterMixin,
    EnumMultipleChoiceField,
    IntChoiceField,
    IntMultipleChoiceField,
)
from .settings import gdx_settings
from .typing import FilterSetMeta

if TYPE_CHECKING:
    from .typing import Any, OrderingFunc

__all__ = [
    "ModelFilterSet",
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


class EnumChoiceFilter(EnumChoiceFilterMixin, django_filters.TypedChoiceFilter):
    """
    Custom field for handling enums better in GraphQL filters.
    Supports a single choice.

    Using `django_filters.ChoiceFilter` causes the enum choices to be converted to strings in GraphQL filters.
    This class uses GraphQL enums instead, which gives better autocomplete results.
    """

    field_class = EnumChoiceField


class EnumMultipleChoiceFilter(EnumChoiceFilterMixin, django_filters.TypedMultipleChoiceFilter):
    """Same as above but supports multiple choices."""

    field_class = EnumMultipleChoiceField


class CustomOrderingFilter(django_filters.OrderingFilter):
    """Ordering filter for handling custom orderings by defining `order_by_{name}` functions on its subclasses."""

    def filter(self, qs: models.QuerySet, value: list[str]) -> models.QuerySet:  # noqa: A003
        if value in EMPTY_VALUES:
            return qs

        ordering: list[str] = list(qs.query.order_by)
        for param in value:
            if param in EMPTY_VALUES:  # pragma: no cover
                continue

            func_name = f"order_by_{param.removeprefix('-')}"

            # Try to find an `ordering_func` on the `OrderingFilter` class or its `FilterSet` class.
            ordering_func: OrderingFunc | None = getattr(self, func_name, None)
            if ordering_func is None and hasattr(self, "parent"):
                ordering_func = getattr(self.parent, func_name, None)

            # If no `ordering_func` was found, just order by the given field name.
            if ordering_func is None or not callable(ordering_func):
                ordering.append(self.get_ordering_value(param))
                continue

            qs = ordering_func(qs, desc=param.startswith("-"))
            # Save the `order_by` value since the `qs.order_by(*ordering)`
            # will clear all ordering when called.
            ordering.extend(qs.query.order_by)

        return qs.order_by(*ordering)


class ModelFilterSet(django_filters.FilterSet):
    """ """

    _meta: FilterSetMeta
    declared_filters: dict[str, django_filters.Filter]

    FILTER_DEFAULTS = FILTER_FOR_DBFIELD_DEFAULTS

    # Change the default filters for all relationships to not make
    # a database query to check if a filtered rows exists.
    FILTER_DEFAULTS[models.ForeignKey] = {"filter_class": IntChoiceFilter}
    FILTER_DEFAULTS[models.OneToOneField] = {"filter_class": IntChoiceFilter}
    FILTER_DEFAULTS[models.ManyToManyField] = {"filter_class": IntMultipleChoiceFilter}
    FILTER_DEFAULTS[models.OneToOneRel] = {"filter_class": IntChoiceFilter}
    FILTER_DEFAULTS[models.ManyToOneRel] = {"filter_class": IntMultipleChoiceFilter}
    FILTER_DEFAULTS[models.ManyToManyRel] = {"filter_class": IntMultipleChoiceFilter}

    class Meta(FilterSetMeta):
        pass

    @classmethod
    def get_filters(cls) -> dict[str, django_filters.Filter]:
        if cls._meta.model is not None:
            # Add a default ordering filter if none is defined, or extend an existing one.
            ordering_fields: list[str | tuple[str, str]] = getattr(cls.Meta, "order_by", ["pk"])
            ordering_filter = cls.declared_filters.get(gdx_settings.ORDERING_FILTER_NAME)

            if isinstance(ordering_filter, CustomOrderingFilter):
                fields_map: dict[str, str] = deepcopy(ordering_filter.param_map)
                for field in ordering_fields:
                    if isinstance(field, tuple):
                        fields_map.setdefault(field[0], field[1])
                    else:
                        fields_map.setdefault(field, field)

                cls.declared_filters[gdx_settings.ORDERING_FILTER_NAME] = CustomOrderingFilter(fields=fields_map)

            elif ordering_filter is None:
                cls.declared_filters[gdx_settings.ORDERING_FILTER_NAME] = CustomOrderingFilter(fields=ordering_fields)

        return super().get_filters()

    def filter_queryset(self, queryset: models.QuerySet) -> models.QuerySet:
        combination_methods: list[str] = getattr(self.Meta, "combination_methods", [])
        combined_values: dict[str, dict[str, Any]] = {key: {} for key in combination_methods}
        combined_filters: dict[str, django_filters.Filter] = {}

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
        if not isinstance(queryset, models.QuerySet):  # pragma: no cover
            msg = f"Expected to receive a QuerySet from filters, but got {type(queryset).__name__} instead."
            raise TypeError(msg)
