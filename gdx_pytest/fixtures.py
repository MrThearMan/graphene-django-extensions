from __future__ import annotations

import pytest

__all__ = [
    "graphql",
    "mock_png",
    "query_counter",
]


@pytest.fixture
def graphql():  # noqa: ANN201
    from graphene_django_extensions.testing import GraphQLClient  # noqa: PLC0415

    return GraphQLClient()


@pytest.fixture
def query_counter():  # pragma: no cover  # noqa: ANN201
    from graphene_django_extensions.testing.utils import capture_database_queries  # noqa: PLC0415

    return capture_database_queries


@pytest.fixture
def mock_png():  # pragma: no cover  # noqa: ANN201
    from graphene_django_extensions.testing.utils import create_mock_png  # noqa: PLC0415

    return create_mock_png()
