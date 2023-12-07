from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from .client import GraphQLClient, QueryData, capture_database_queries

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

    from pytest_django.fixtures import SettingsWrapper

    from ..typing import Callable


@pytest.fixture()
def graphql() -> GraphQLClient:  # pragma: no cover
    return GraphQLClient()


@pytest.fixture()
def query_counter(settings: SettingsWrapper) -> Callable[[], AbstractContextManager[QueryData]]:  # pragma: no cover
    settings.DEBUG = True
    return capture_database_queries
