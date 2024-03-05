from __future__ import annotations

from typing import TYPE_CHECKING

import django_filters
from django import forms
from django.db import models
from django.db.models import Model, Q, QuerySet
from django.db.models.constants import LOOKUP_SEP
from django_filters.constants import ALL_FIELDS, EMPTY_VALUES
from django_filters.filterset import FILTER_FOR_DBFIELD_DEFAULTS
from graphene.utils.str_converters import to_camel_case
from query_optimizer.filter import FilterSet

from .fields import (
    EnumChoiceField,
    EnumMultipleChoiceField,
    IntChoiceField,
    IntMultipleChoiceField,
    OrderByField,
    UserDefinedFilterField,
)
from .settings import gdx_settings
from .typing import (
    FieldAliasToLookup,
    FilterFields,
    FilterSetMeta,
    UserDefinedFilterInput,
    UserDefinedFilterResult,
)

if TYPE_CHECKING:
    from .typing import Any, OrderingFunc

__all__ = [
    "CustomOrderingFilter",
    "EnumChoiceFilter",
    "EnumMultipleChoiceFilter",
    "IntChoiceFilter",
    "IntMultipleChoiceFilter",
    "ModelFilterSet",
    "UserDefinedFilter",
]


class EnumChoiceFilterMixin:
    def __init__(self, enum: type[models.Choices], *args: Any, **kwargs: Any) -> None:
        kwargs["enum"] = enum
        kwargs["choices"] = enum.choices
        super().__init__(*args, **kwargs)


class IntChoiceFilter(django_filters.TypedChoiceFilter):
    """
    Allow plain integers as choices in GraphQL filters.
    Normally, integer enums are converted to string enums in GraphQL by prefixing
    them with `A_`, but this filter allows using plain integers.
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


class UserDefinedFilter(django_filters.Filter):
    """Allows for user defined filter operations."""

    field_class = UserDefinedFilterField

    def __init__(self, model: type[Model], fields: FilterFields = ALL_FIELDS, **kwargs: Any) -> None:
        kwargs["model"] = model
        kwargs["fields"] = self._normalize_fields(model, fields)
        super().__init__(**kwargs)

    def filter(self, qs: QuerySet, data: UserDefinedFilterInput) -> QuerySet:
        if data in EMPTY_VALUES:
            return qs

        result = self.build_user_defined_filters(data)

        if result.annotations:  # pragma: no cover
            qs = qs.annotate(**result.annotations)
        if result.ordering:  # pragma: no cover
            qs = qs.order_by(*qs.query.order_by, *result.ordering)

        return qs.filter(result.filters)

    def build_user_defined_filters(self, data: UserDefinedFilterInput) -> UserDefinedFilterResult:
        filters: Q = Q()
        ann: dict[str, Any] = {}
        ordering: list[str] = []

        if data.operation.value in ("AND", "OR", "XOR", "NOT"):
            if data.operations is None:
                msg = "Logical filter operation requires 'operations' to be set."
                raise ValueError(msg)

            if data.operation.value == "NOT" and len(data.operations) != 1:
                msg = "Logical filter operation 'NOT' requires exactly one operation."
                raise ValueError(msg)

            for operation in data.operations:
                result = self.build_user_defined_filters(operation)
                if result.annotations:  # pragma: no cover
                    ann.update(result.annotations)
                if result.ordering:  # pragma: no cover
                    ordering.extend(result.ordering)

                if data.operation.value == "AND":
                    filters &= result.filters
                elif data.operation.value == "OR":
                    filters |= result.filters
                elif data.operation.value == "NOT":
                    filters = ~result.filters
                elif data.operation.value == "XOR":
                    filters ^= result.filters

        else:
            if data.field is None:
                msg = "Comparison filter operation requires 'field' to be set."
                raise ValueError(msg)

            alias: str = getattr(data.field, "name", data.field)
            field: str = self.extra["fields"][alias]
            inputs: dict[str, Any] = {f"{field}{LOOKUP_SEP}{data.operation.value.lower()}": data.value}
            filters = Q(**inputs)

        return UserDefinedFilterResult(filters=filters, annotations=ann, ordering=ordering)

    @staticmethod
    def _normalize_fields(model: type[Model], fields: FilterFields) -> FieldAliasToLookup:
        if fields == ALL_FIELDS:  # pragma: no cover
            return {to_camel_case(field.name): field.name for field in model._meta.get_fields()}

        normalized_fields: FieldAliasToLookup = {}
        for field in fields:
            if isinstance(field, tuple):
                normalized_fields[to_camel_case(field[1])] = field[0]
            else:
                normalized_fields[to_camel_case(field)] = field
        return normalized_fields


class CustomOrderingFilter(django_filters.OrderingFilter):
    """
    Ordering filter for handling custom orderings by defining `order_by_{name}` functions
    on its subclasses or filtersets it is defined on.
    """

    base_field_class = OrderByField
    field_class = forms.Field

    def filter(self, qs: models.QuerySet, value: list[str]) -> models.QuerySet:
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


class ModelFilterSet(FilterSet):
    """
    Custom FilterSet class for optimizing the filtering of GraphQL queries.
    Adds the following features to all types that inherit it:

    - Adds a default ordering filter by primary key if none is defined.

    - Changes the default filters for all relationships to not make a database
      query to check if a filtered rows exists.

    ---

    The following options can be set in the `Meta`-class.

    `model: type[models.Model]`

    - Required. Model class for the model the filterset is for.

    `fields: Sequence[FieldNameStr] | Mapping[FieldNameStr, Sequence[LookupNameStr]] | Literal["__all__"]`

    - Required if no `exclude`. Fields to include in the filterset. Can be a list of field names
      (lookup name will be `exact`), a mapping of field names to a list of lookup names, or the
      special value `__all__` to include all fields.

    `exclude: Sequence[FieldNameStr]`

    - Required if no `fields`. Fields to exclude from the filterset.

    `filter_overrides: dict[Field, FilterOverride]`

    - Optional. Overrides for the default filters for specific fields.

    `form: type[Form]`

    - Optional. Form class to use for the filterset. Defaults to `django_filters.Form`.

    `order_by: Sequence[FieldLookupStr | tuple[FieldLookupStr, FilterAliasStr]]`

    - Optional. Ordering filters to add to the filterset. Can also add non-field orderings,
      or customize field orderings by adding a `order_by_{field_name}` method to the
      `ModelFilterSet` subclass.

    `combination_methods: Sequence[MethodNameStr]`

    - Optional. Allows combining method filters so that they will use the same filter function.
      The combination method will always run, and its value will be a mapping of the
      field names of the combined filters to their values.
    """

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

            if isinstance(ordering_filter, CustomOrderingFilter):  # pragma: no cover
                # Param map should be flipped so that OrderingFilter initializes correctly.
                fields_map: dict[str, str] = {v: k for k, v in ordering_filter.param_map.items()}
                for field in ordering_fields:
                    if isinstance(field, tuple):
                        fields_map.setdefault(field[0], field[1])
                    else:
                        fields_map.setdefault(field, field)

                cls.declared_filters[gdx_settings.ORDERING_FILTER_NAME] = CustomOrderingFilter(
                    model=cls._meta.model,
                    fields=fields_map,
                )

            elif ordering_filter is None:
                cls.declared_filters[gdx_settings.ORDERING_FILTER_NAME] = CustomOrderingFilter(
                    model=cls._meta.model,
                    fields=ordering_fields,
                )

        if cls._meta.fields is None and cls.declared_filters:
            cls._meta.fields = []

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
