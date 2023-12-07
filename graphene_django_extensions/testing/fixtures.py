from contextlib import AbstractContextManager
from typing import Callable

import pytest

from .client import GraphQLClient, QueryData, capture_database_queries


@pytest.fixture()
def graphql() -> GraphQLClient:
    return GraphQLClient()


@pytest.fixture()
def query_counter(settings) -> Callable[[], AbstractContextManager[QueryData]]:  # noqa: ANN001
    settings.DEBUG = True
    return capture_database_queries
