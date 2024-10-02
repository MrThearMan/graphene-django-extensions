from __future__ import annotations

from typing import TYPE_CHECKING

from example_project.app.models import (
    Example,
    ExampleState,
    ForwardManyToMany,
    ForwardManyToOne,
    ForwardOneToOne,
    ReverseManyToMany,
    ReverseOneToMany,
    ReverseOneToOne,
)
from graphene_django_extensions.filters import (
    EnumMultipleChoiceFilter,
    IntChoiceFilter,
    IntMultipleChoiceFilter,
    ModelFilterSet,
    UserDefinedFilter,
)

if TYPE_CHECKING:
    from django.db import models

__all__ = [
    "ExampleFilterSet",
    "ForwardManyToManyFilterSet",
    "ForwardManyToOneFilterSet",
    "ForwardOneToOneFilterSet",
    "ReverseManyToManyFilterSet",
    "ReverseOneToManyFilterSet",
    "ReverseOneToOneFilterSet",
]


class ExampleFilterSet(ModelFilterSet):
    pk = IntMultipleChoiceFilter()
    forward_one_to_one_field = IntMultipleChoiceFilter()

    example_state = EnumMultipleChoiceFilter(enum=ExampleState)

    one = IntChoiceFilter(method="filter_by_custom")
    two = IntChoiceFilter(method="filter_by_custom")

    filter = UserDefinedFilter(
        model=Example,
        fields=[
            "pk",
            "name",
            "name_en",
            "name_fi",
            "number",
            "email",
            ("forward_one_to_one_field__name", "foto_name"),
            "reverse_many_to_many_rels__name",
            ("forward_many_to_many_fields__name", "fmtm_name"),
        ],
    )

    class Meta:
        model = Example
        fields = [
            "pk",
            "name",
            "name_en",
            "name_fi",
            "number",
            "email",
            "example_state",
        ]
        order_by = [
            "pk",
            "name",
            "name_en",
            "name_fi",
            "number",
            "email",
            ("forward_one_to_one_field", "foto"),
            ("forward_many_to_one_field", "many_to_one"),
            "custom",
        ]
        combination_methods = [
            "filter_by_custom",
        ]

    def filter_by_custom(self, qs: models.QuerySet, name: str, values: dict[str, int | None]) -> models.QuerySet:
        numbers: list[int] = [value for value in values.values() if value is not None]
        if not numbers:
            return qs
        return qs.filter(number__in=numbers)

    def order_by_custom(self, qs: models.QuerySet, *, desc: bool) -> models.QuerySet:
        return qs.order_by("-number" if desc else "number")


class ForwardOneToOneFilterSet(ModelFilterSet):
    pk = IntMultipleChoiceFilter()

    class Meta:
        model = ForwardOneToOne
        fields = ["pk"]


class ForwardManyToOneFilterSet(ModelFilterSet):
    pk = IntMultipleChoiceFilter()

    class Meta:
        model = ForwardManyToOne
        fields = ["pk"]


class ForwardManyToManyFilterSet(ModelFilterSet):
    pk = IntMultipleChoiceFilter()

    class Meta:
        model = ForwardManyToMany
        fields = ["pk"]


class ReverseOneToOneFilterSet(ModelFilterSet):
    pk = IntMultipleChoiceFilter()

    class Meta:
        model = ReverseOneToOne
        fields = ["pk"]


class ReverseOneToManyFilterSet(ModelFilterSet):
    pk = IntMultipleChoiceFilter()

    class Meta:
        model = ReverseOneToMany
        fields = ["pk"]


class ReverseManyToManyFilterSet(ModelFilterSet):
    pk = IntMultipleChoiceFilter()

    class Meta:
        model = ReverseManyToMany
        fields = ["pk"]
