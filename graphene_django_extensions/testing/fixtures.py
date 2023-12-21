from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ..typing import NamedTuple, TypedDict, TypeVar
from .client import GraphQLClient, QueryData, capture_database_queries

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

    from pytest_django.fixtures import SettingsWrapper

    from ..typing import Callable


__all__ = [
    "graphql",
    "parametrize_helper",
    "query_counter",
]


@pytest.fixture()
def graphql() -> GraphQLClient:  # pragma: no cover
    return GraphQLClient()


@pytest.fixture()
def query_counter(settings: SettingsWrapper) -> Callable[[], AbstractContextManager[QueryData]]:  # pragma: no cover
    settings.DEBUG = True
    return capture_database_queries


TNamedTuple = TypeVar("TNamedTuple", bound=NamedTuple)


class ParametrizeArgs(TypedDict):
    argnames: list[str]
    argvalues: list[TNamedTuple]
    ids: list[str]


def parametrize_helper(__tests: dict[str, TNamedTuple], /) -> ParametrizeArgs:
    """Construct parametrize input while setting test IDs."""
    assert __tests, "I need some tests, please!"  # noqa: S101
    values = list(__tests.values())
    try:
        return ParametrizeArgs(
            argnames=list(values[0].__class__.__annotations__),
            argvalues=values,
            ids=list(__tests),
        )
    except AttributeError as error:  # pragma: no cover
        msg = "Improper configuration. Did you use a NamedTuple for TNamedTuple?"
        raise RuntimeError(msg) from error
