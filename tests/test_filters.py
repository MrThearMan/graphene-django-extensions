from __future__ import annotations

import re
from typing import TYPE_CHECKING

import django_filters
import pytest
from django.db.models import Q
from django.db.models.functions import Length

from example_project.app.models import Example, ForwardOneToOne
from graphene_django_extensions.constants import Operation
from graphene_django_extensions.filters import CustomOrderingFilter, ModelFilterSet, UserDefinedFilter
from graphene_django_extensions.typing import UserDefinedFilterInput, UserDefinedFilterResult
from tests.factories import ExampleFactory

if TYPE_CHECKING:
    from django.db import models

pytestmark = [
    pytest.mark.django_db,
]


class NameLengthFilter(UserDefinedFilter):
    """User defined filter that adds a 'nameLength' field, which needs an annotation."""

    def build_user_defined_filters(self, data: UserDefinedFilterInput) -> UserDefinedFilterResult:
        if data.field == "nameLength":
            lookup = f"name_length__{data.operation.value.lower()}"
            return UserDefinedFilterResult(
                filters=[Q(**{lookup: data.value})],
                annotations={"name_length": Length("name")},
                ordering=["name_length"],
            )
        return super().build_user_defined_filters(data)


def test_user_defined_filter__all_fields_by_default():
    ftr = UserDefinedFilter(model=ForwardOneToOne)

    assert ftr.extra["fields"]["id"] == "id"
    assert ftr.extra["fields"]["name"] == "name"
    assert ftr.extra["fields"]["exampleRel"] == "example_rel"


def test_user_defined_filter__all__requires_operations():
    ftr = UserDefinedFilter(model=Example, fields=["name"])
    data = UserDefinedFilterInput(operation=Operation.ALL)

    with pytest.raises(ValueError, match=re.escape("The 'ALL' filter operation requires 'operations' to be set.")):
        ftr.filter(Example.objects.all(), data)


def test_user_defined_filter__annotations_and_ordering():
    ExampleFactory.create(name="foo")
    long_name = ExampleFactory.create(name="foobar")
    longest_name = ExampleFactory.create(name="foobarbaz")

    ftr = NameLengthFilter(model=Example, fields=["name"])
    data = UserDefinedFilterInput(operation=Operation.GT, field="nameLength", value=3)

    qs = ftr.filter(Example.objects.all(), data)

    assert list(qs) == [long_name, longest_name]


@pytest.mark.parametrize("operation", [Operation.ALL, Operation.AND])
def test_user_defined_filter__annotations_and_ordering__nested(operation):
    ExampleFactory.create(name="foo")
    ExampleFactory.create(name="foobar")
    longest_name = ExampleFactory.create(name="foobarbaz")

    ftr = NameLengthFilter(model=Example, fields=["name"])
    data = UserDefinedFilterInput(
        operation=operation,
        operations=[
            UserDefinedFilterInput(operation=Operation.GT, field="nameLength", value=3),
            UserDefinedFilterInput(operation=Operation.ENDSWITH, field="name", value="baz"),
        ],
    )

    qs = ftr.filter(Example.objects.all(), data)

    assert list(qs) == [longest_name]


def test_custom_ordering_filter__keeps_existing_ordering():
    ftr = CustomOrderingFilter(fields=["email"])

    qs = ftr.filter(Example.objects.order_by("-number"), ["email"])

    assert qs.query.order_by == ("-number", "email")


def test_custom_ordering_filter__skips_empty_values():
    ftr = CustomOrderingFilter(fields=["name", "number"])

    qs = ftr.filter(Example.objects.all(), ["", "-number"])

    assert qs.query.order_by == ("-number",)


def test_custom_ordering_filter__without_filterset():
    # A filter that is not bound to a filterset has no 'parent' to look for ordering functions in.
    ftr = CustomOrderingFilter(fields=["email"])

    qs = ftr.filter(Example.objects.all(), ["-email"])

    assert qs.query.order_by == ("-email",)


def test_model_filterset__extend_custom_ordering_filter():
    class ExampleOrderingFilterSet(ModelFilterSet):
        order_by = CustomOrderingFilter(fields=[("email", "mail")])

        class Meta:
            model = Example
            fields = ["name"]
            order_by = ["name", ("number", "num"), ("email", "ignored")]

    ordering_filter = ExampleOrderingFilterSet.base_filters["order_by"]

    assert isinstance(ordering_filter, CustomOrderingFilter)
    # Explicitly defined orderings are kept, and the ones from `Meta.order_by` are added.
    assert ordering_filter.param_map == {"mail": "email", "name": "name", "num": "number"}


def test_model_filterset__keep_other_ordering_filter():
    ordering_filter = django_filters.OrderingFilter(fields=["name"])

    class ExampleOrderingFilterSet(ModelFilterSet):
        order_by = ordering_filter

        class Meta:
            model = Example
            fields = ["name"]

    assert ExampleOrderingFilterSet.base_filters["order_by"] is ordering_filter


def test_model_filterset__filter_must_return_queryset():
    class ExampleBrokenFilterSet(ModelFilterSet):
        name = django_filters.CharFilter(method="filter_name")

        class Meta:
            model = Example
            fields = ["name"]

        def filter_name(self, qs: models.QuerySet, name: str, value: str) -> list[Example]:
            return list(qs.filter(name=value))

    filterset = ExampleBrokenFilterSet(data={"name": "foo"}, queryset=Example.objects.all())

    msg = "Expected to receive a QuerySet from filters, but got list instead."
    with pytest.raises(TypeError, match=re.escape(msg)):
        filterset.qs  # noqa: B018
