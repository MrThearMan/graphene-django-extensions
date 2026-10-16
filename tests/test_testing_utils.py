from typing import NamedTuple

import pytest
from django.db import connection

from graphene_django_extensions.testing.utils import capture_database_queries, parametrize_helper

pytestmark = [
    pytest.mark.django_db,
]


def test_capture_database_queries__params_interpolated():
    with capture_database_queries() as results, connection.cursor() as cursor:
        cursor.execute("SELECT %s", (1,))

    assert results.queries == ["SELECT 1"]


def test_capture_database_queries__list_params_interpolated():
    with capture_database_queries() as results, connection.cursor() as cursor:
        cursor.execute("SELECT %s, %s", [1, 2])

    assert results.queries == ["SELECT 1, 2"]


def test_capture_database_queries__no_params():
    # Raw queries without parameters cannot be interpolated, so they are captured as is.
    with capture_database_queries() as results, connection.cursor() as cursor:
        cursor.execute("SELECT 1")

    assert results.queries == ["SELECT 1"]


def test_capture_database_queries__log():
    with capture_database_queries() as results, connection.cursor() as cursor:
        cursor.execute("SELECT 1")

    assert ">>> Queries (1):" in results.log
    assert "SELECT 1" in results.log


class Params(NamedTuple):
    value: int
    expected: int


def test_parametrize_helper():
    args = parametrize_helper({"one": Params(value=1, expected=1), "two": Params(value=2, expected=2)})

    assert args == {
        "argnames": ["value", "expected"],
        "argvalues": [Params(value=1, expected=1), Params(value=2, expected=2)],
        "ids": ["one", "two"],
    }


def test_parametrize_helper__not_named_tuple():
    with pytest.raises(RuntimeError, match="Did you use a NamedTuple"):
        parametrize_helper({"one": 1})
