import pytest

from graphene_django_extensions.testing import GraphQLClient
from tests.factories import ExampleFactory

pytestmark = [
    pytest.mark.django_db,
]


def test_connection__total_count(graphql: GraphQLClient):
    ExampleFactory.create()
    query = """
        query {
            examples {
                edges {
                    node {
                        pk
                    }
                }
                totalCount
            }
        }
    """
    graphql.login_with_superuser()
    response = graphql(query)
    assert response.has_errors is False, response
    assert response.first_query_object.get("totalCount") == 1, response
