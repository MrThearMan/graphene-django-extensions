from typing import Any, NamedTuple

import pytest

from graphene_django_extensions.utils import get_nested

Sentinel = object()


class Params(NamedTuple):
    value: dict | list | None
    args: list[str | int]
    default: Any
    expected: Any


@pytest.mark.parametrize(
    ("value", "args", "default", "expected"),
    [
        Params(
            value={"foo": 1},
            args=["foo"],
            default=Sentinel,
            expected=1,
        ),
        Params(
            value={"foo": {"bar": 1}},
            args=["foo", "bar"],
            default=Sentinel,
            expected=1,
        ),
        Params(
            value={"foo": {"bar": {"baz": 1}}},
            args=["foo", "bar", "baz"],
            default=Sentinel,
            expected=1,
        ),
        Params(
            value=[1, 2],
            args=[0],
            default=Sentinel,
            expected=1,
        ),
        Params(
            value=[[1, 2]],
            args=[0, 0],
            default=Sentinel,
            expected=1,
        ),
        Params(
            value=[[[1, 2]]],
            args=[0, 0, 0],
            default=Sentinel,
            expected=1,
        ),
        Params(
            value={"foo": [1]},
            args=["foo", 0],
            default=Sentinel,
            expected=1,
        ),
        Params(
            value=[{"foo": 1}],
            args=[0, "foo"],
            default=Sentinel,
            expected=1,
        ),
        Params(
            value={"foo": [{"bar": 1}]},
            args=["foo", 0, "bar"],
            default=Sentinel,
            expected=1,
        ),
        Params(
            value=[{"foo": [1]}],
            args=[0, "foo", 0],
            default=Sentinel,
            expected=1,
        ),
        Params(
            value=None,
            args=["foo"],
            default=1,
            expected=1,
        ),
        Params(
            value={"foo": None},
            args=["foo", "bar"],
            default=1,
            expected=1,
        ),
        Params(
            value=None,
            args=["foo", "bar", "baz"],
            default=1,
            expected=1,
        ),
        Params(
            value=None,
            args=[0],
            default=1,
            expected=1,
        ),
        Params(
            value=[None],
            args=[0, 0],
            default=1,
            expected=1,
        ),
        Params(
            value=None,
            args=[0, 0, 0],
            default=1,
            expected=1,
        ),
    ],
    ids=[
        "One layer dict",
        "Two layer dict",
        "Three layer dict",
        "One layer list",
        "Two layer list",
        "Three layer list",
        "One layer dict with one layer list",
        "One layer list with one layer dict",
        "One layer dict with one layer list with one layer dict",
        "One layer list with one layer dict with one layer list",
        "One layer default dict",
        "Two layer default dict",
        "Three layer default dict",
        "One layer default list",
        "Two layer default list",
        "Three layer default list",
    ],
)
def test_get_nested(value, args, default, expected):
    assert get_nested(value, *args, default=default) == expected
