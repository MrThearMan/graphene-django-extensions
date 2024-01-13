from django.db import models

from graphene_django_extensions.filters import (
    EnumMultipleChoiceFilter,
    IntChoiceFilter,
    IntMultipleChoiceFilter,
    ModelFilterSet,
    UserDefinedFilter,
)
from tests.example.models import Example, ExampleState


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
            "number",
            "email",
            ("forward_one_to_one_field__name", "foto_name"),
        ],
    )

    class Meta:
        model = Example
        fields = [
            "pk",
            "name",
            "number",
            "email",
            "example_state",
        ]
        order_by = [
            "pk",
            "name",
            "number",
            "email",
            ("forward_one_to_one_field", "foto"),
        ]
        combination_methods = [
            "filter_by_custom",
        ]

    def filter_by_custom(self, qs: models.QuerySet, name: str, values: dict[str, int | None]) -> models.QuerySet:
        numbers: list[int] = [value for value in values.values() if value is not None]
        if not numbers:
            return qs
        return qs.filter(number__in=numbers)

    def order_by_number(self, qs: models.QuerySet, *, desc: bool) -> models.QuerySet:
        return qs.order_by("-number" if desc else "number")
