import re
from typing import Any, NamedTuple

import pytest
from django.db import models

from graphene_django_extensions.filters import UserDefinedFilter
from graphene_django_extensions.testing.fixtures import parametrize_helper
from graphene_django_extensions.typing import Operation, UserDefinedFilterInput
from graphene_django_extensions.utils import get_nested
from tests.example.models import Example

Sentinel = object()


class GetNestedParams(NamedTuple):
    value: dict | list | None
    args: list[str | int]
    default: Any
    expected: Any


@pytest.mark.parametrize(
    **parametrize_helper(
        {
            "One layer dict": GetNestedParams(
                value={"foo": 1},
                args=["foo"],
                default=Sentinel,
                expected=1,
            ),
            "Two layer dict": GetNestedParams(
                value={"foo": {"bar": 1}},
                args=["foo", "bar"],
                default=Sentinel,
                expected=1,
            ),
            "Three layer dict": GetNestedParams(
                value={"foo": {"bar": {"baz": 1}}},
                args=["foo", "bar", "baz"],
                default=Sentinel,
                expected=1,
            ),
            "One layer list": GetNestedParams(
                value=[1, 2],
                args=[0],
                default=Sentinel,
                expected=1,
            ),
            "Two layer list": GetNestedParams(
                value=[[1, 2]],
                args=[0, 0],
                default=Sentinel,
                expected=1,
            ),
            "Three layer list": GetNestedParams(
                value=[[[1, 2]]],
                args=[0, 0, 0],
                default=Sentinel,
                expected=1,
            ),
            "One layer dict with one layer list": GetNestedParams(
                value={"foo": [1]},
                args=["foo", 0],
                default=Sentinel,
                expected=1,
            ),
            "One layer list with one layer dict": GetNestedParams(
                value=[{"foo": 1}],
                args=[0, "foo"],
                default=Sentinel,
                expected=1,
            ),
            "One layer dict with one layer list with one layer dict": GetNestedParams(
                value={"foo": [{"bar": 1}]},
                args=["foo", 0, "bar"],
                default=Sentinel,
                expected=1,
            ),
            "One layer list with one layer dict with one layer list": GetNestedParams(
                value=[{"foo": [1]}],
                args=[0, "foo", 0],
                default=Sentinel,
                expected=1,
            ),
            "One layer default dict": GetNestedParams(
                value=None,
                args=["foo"],
                default=1,
                expected=1,
            ),
            "Two layer default dict": GetNestedParams(
                value={"foo": None},
                args=["foo", "bar"],
                default=1,
                expected=1,
            ),
            "Three layer default dict": GetNestedParams(
                value=None,
                args=["foo", "bar", "baz"],
                default=1,
                expected=1,
            ),
            "One layer default list": GetNestedParams(
                value=None,
                args=[0],
                default=1,
                expected=1,
            ),
            "Two layer default list": GetNestedParams(
                value=[None],
                args=[0, 0],
                default=1,
                expected=1,
            ),
            "Three layer default list": GetNestedParams(
                value=None,
                args=[0, 0, 0],
                default=1,
                expected=1,
            ),
        }
    )
)
def test_get_nested(value, args, default, expected):
    assert get_nested(value, *args, default=default) == expected


class FilterOperationParams(NamedTuple):
    op: UserDefinedFilterInput
    result: models.Q


@pytest.mark.parametrize(
    **parametrize_helper(
        {
            "exact": FilterOperationParams(
                op=UserDefinedFilterInput(
                    operation=Operation.EXACT,
                    field="foo",
                    value=1,
                ),
                result=models.Q(foo__exact=1),
            ),
            "contains": FilterOperationParams(
                op=UserDefinedFilterInput(
                    operation=Operation.CONTAINS,
                    field="foo",
                    value=1,
                ),
                result=models.Q(foo__contains=1),
            ),
            "and": FilterOperationParams(
                op=UserDefinedFilterInput(
                    operation=Operation.AND,
                    operations=[
                        UserDefinedFilterInput(
                            operation=Operation.GTE,
                            field="foo",
                            value=1,
                        ),
                        UserDefinedFilterInput(
                            operation=Operation.LTE,
                            field="foo",
                            value=10,
                        ),
                    ],
                ),
                result=models.Q(foo__gte=1) & models.Q(foo__lte=10),
            ),
            "or": FilterOperationParams(
                op=UserDefinedFilterInput(
                    operation=Operation.OR,
                    operations=[
                        UserDefinedFilterInput(
                            operation=Operation.GT,
                            field="foo",
                            value=1,
                        ),
                        UserDefinedFilterInput(
                            operation=Operation.LT,
                            field="foo",
                            value=10,
                        ),
                    ],
                ),
                result=models.Q(foo__gt=1) | models.Q(foo__lt=10),
            ),
            "xor": FilterOperationParams(
                op=UserDefinedFilterInput(
                    operation=Operation.XOR,
                    operations=[
                        UserDefinedFilterInput(
                            operation=Operation.GT,
                            field="foo",
                            value=1,
                        ),
                        UserDefinedFilterInput(
                            operation=Operation.LT,
                            field="foo",
                            value=10,
                        ),
                    ],
                ),
                result=models.Q(foo__gt=1) ^ models.Q(foo__lt=10),
            ),
            "not": FilterOperationParams(
                op=UserDefinedFilterInput(
                    operation=Operation.NOT,
                    operations=[
                        UserDefinedFilterInput(
                            operation=Operation.ENDSWITH,
                            field="foo",
                            value="bar",
                        ),
                    ],
                ),
                result=~models.Q(foo__endswith="bar"),
            ),
            "in": FilterOperationParams(
                op=UserDefinedFilterInput(
                    operation=Operation.IN,
                    field="foo",
                    value=[1, 2, 3, 4],
                ),
                result=models.Q(foo__in=[1, 2, 3, 4]),
            ),
        },
    ),
)
def test_build_filter_operation(op, result):
    user_filter = UserDefinedFilter(Example, fields=["foo"])
    filter_result = user_filter.build_user_defined_filters(op)
    assert filter_result.filters == result


def test_build_filter_operation__no_field_set():
    user_filter = UserDefinedFilter(Example, fields=["foo"])
    op = UserDefinedFilterInput(operation=Operation.EXACT)

    msg = "Comparison filter operation requires 'field' to be set."
    with pytest.raises(ValueError, match=re.escape(msg)):
        user_filter.build_user_defined_filters(op)


def test_build_filter_operation__no_operations():
    user_filter = UserDefinedFilter(Example, fields=["foo"])
    op = UserDefinedFilterInput(operation=Operation.AND)

    msg = "Logical filter operation requires 'operations' to be set."
    with pytest.raises(ValueError, match=re.escape(msg)):
        user_filter.build_user_defined_filters(op)


def test_build_filter_operation__not_should_have_only_one_operation():
    user_filter = UserDefinedFilter(Example, fields=["foo"])
    op = UserDefinedFilterInput(
        operation=Operation.NOT,
        operations=[
            UserDefinedFilterInput(operation=Operation.EXACT, field="foo", value=1),
            UserDefinedFilterInput(operation=Operation.CONTAINS, field="foo", value=1),
        ],
    )

    msg = "Logical filter operation 'NOT' requires exactly one operation."
    with pytest.raises(ValueError, match=re.escape(msg)):
        user_filter.build_user_defined_filters(op)
