import pytest

from graphene_django_extensions.testing import GraphQLClient, build_query
from tests.factories import ExampleFactory

pytestmark = [
    pytest.mark.django_db,
]


def test_graphql__ordering__ascending(graphql: GraphQLClient):
    example_1 = ExampleFactory.create(name="foo2")
    example_2 = ExampleFactory.create(name="foo1")

    query = build_query("examples", connection=True, order_by="nameEnAsc")

    graphql.login_with_superuser()
    response = graphql(query)

    assert response.has_errors is False, response
    assert len(response.edges) == 2
    assert response.node(0) == {"pk": example_2.pk}
    assert response.node(1) == {"pk": example_1.pk}


def test_graphql__ordering__descending(graphql: GraphQLClient):
    example_1 = ExampleFactory.create(name="foo2")
    example_2 = ExampleFactory.create(name="foo1")

    query = build_query("examples", connection=True, order_by="nameEnDesc")

    graphql.login_with_superuser()
    response = graphql(query)

    assert response.has_errors is False, response
    assert len(response.edges) == 2
    assert response.node(0) == {"pk": example_1.pk}
    assert response.node(1) == {"pk": example_2.pk}


def test_graphql__ordering__multiple(graphql: GraphQLClient):
    example_1 = ExampleFactory.create(name="foo2", number=1)
    example_2 = ExampleFactory.create(name="foo1", number=2)

    query = build_query("examples", connection=True, order_by=["nameEnAsc", "numberDesc"])

    graphql.login_with_superuser()
    response = graphql(query)

    assert response.has_errors is False, response
    assert len(response.edges) == 2
    assert response.node(0) == {"pk": example_2.pk}
    assert response.node(1) == {"pk": example_1.pk}


def test_graphql__ordering__custom_function(graphql: GraphQLClient):
    example_1 = ExampleFactory.create(number=2)
    example_2 = ExampleFactory.create(number=1)

    query = build_query("examples", connection=True, order_by="customAsc")

    graphql.login_with_superuser()
    response = graphql(query)

    assert response.has_errors is False, response
    assert len(response.edges) == 2
    assert response.node(0) == {"pk": example_2.pk}
    assert response.node(1) == {"pk": example_1.pk}
