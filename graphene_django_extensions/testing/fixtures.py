from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from .client import GraphQLClient, QueryData, capture_database_queries

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

    from ..typing import Callable


@pytest.fixture()
def graphql() -> GraphQLClient:
    return GraphQLClient()


@pytest.fixture()
def query_counter(settings) -> Callable[[], AbstractContextManager[QueryData]]:  # noqa: ANN001
    settings.DEBUG = True
    return capture_database_queries
