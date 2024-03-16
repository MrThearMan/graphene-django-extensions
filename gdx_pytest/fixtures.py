from __future__ import annotations

import pytest

__all__ = [
    "graphql",
    "mock_png",
    "query_counter",
]


@pytest.fixture()
def graphql():  # noqa: ANN201
    from graphene_django_extensions.testing import GraphQLClient

    return GraphQLClient()


@pytest.fixture()
def query_counter():  # pragma: no cover  # noqa: ANN201
    from graphene_django_extensions.testing.utils import capture_database_queries

    return capture_database_queries


@pytest.fixture()
def mock_png():  # pragma: no cover  # noqa: ANN201
    from graphene_django_extensions.testing.utils import create_mock_png

    return create_mock_png()
