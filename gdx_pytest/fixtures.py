from __future__ import annotations

import pytest

__all__ = [
    "graphql",
    "query_counter",
]


@pytest.fixture()
def graphql():  # noqa: ANN201
    from graphene_django_extensions.testing import GraphQLClient

    return GraphQLClient()


@pytest.fixture()
def query_counter():  # pragma: no cover  # noqa: ANN201
    from graphene_django_extensions.testing.client import capture_database_queries

    return capture_database_queries
