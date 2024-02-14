from unittest.mock import patch

import pytest

from graphene_django_extensions.testing import GraphQLClient, build_query
from graphene_django_extensions.typing import GQLInfo
from graphene_django_extensions.utils import get_filters_from_info, get_fields_from_info
from tests.example.models import ExampleState
from tests.factories import ExampleFactory, ForwardManyToManyFactory

pytestmark = [
    pytest.mark.django_db,
]


def test_graphql__filter(graphql: GraphQLClient):
    example = ExampleFactory.create(name="foo", example_state=ExampleState.ACTIVE)
    ExampleFactory.create(name="foobar")

    query = build_query(
        "examples",
        connection=True,
        name=example.name,
        example_state=[ExampleState.ACTIVE, ExampleState.INACTIVE],
    )

    graphql.login_with_superuser()
    response = graphql(query)

    assert response.has_errors is False, response
    assert len(response.edges) == 1
    assert response.node() == {"pk": example.pk}


def test_graphql__filter__relation(graphql: GraphQLClient):
    # Test that filtering via a relation does not make an additional query
    # to fetch related items for checking whether the related objects exist.
    example = ExampleFactory.create(name="foo")
    ExampleFactory.create(name="foobar")

    query = build_query("examples", connection=True, forward_one_to_one_field=example.forward_one_to_one_field.pk)

    graphql.login_with_superuser()
    response = graphql(query)

    assert response.has_errors is False, response
    assert len(response.edges) == 1
    assert response.node() == {"pk": example.pk}

    # 1) Get session
    # 2) Get user
    # 3) Count objects for pagination
    # 4) Fetch for objects
    response.assert_query_count(4)


def test_graphql__filter__combination_filter(graphql: GraphQLClient):
    example_1 = ExampleFactory.create(name="foo1", number=1)
    example_2 = ExampleFactory.create(name="foo2", number=2)

    query = build_query("examples", connection=True, order_by="nameAsc", one=example_1.number, two=example_2.number)

    graphql.login_with_superuser()
    response = graphql(query)

    assert response.has_errors is False, response
    assert len(response.edges) == 2
    assert response.node(0) == {"pk": example_1.pk}
    assert response.node(1) == {"pk": example_2.pk}


def test_graphql__filter__user_defined(graphql: GraphQLClient):
    example = ExampleFactory.create(name="foo")
    ExampleFactory.create(name="foobar")

    query = """
        query {
          examples(
            filter: {
              field: name,
              operation: EXACT,
              value: "foo",
            }
          ) {
            edges {
              node {
                pk
              }
            }
          }
        }
    """

    graphql.login_with_superuser()

    fields = {}
    filters = {}

    def tracker(info: GQLInfo):
        nonlocal fields, filters
        fields = get_fields_from_info(info)
        filters = get_filters_from_info(info)
        return filters

    with patch("graphene_django_extensions.bases.get_filters_from_info", side_effect=tracker):
        response = graphql(query)

    assert fields == [{"examples": [{"edges": [{"node": ["pk"]}]}]}]
    assert filters == {"examples": {"filter": {"field": "name", "operation": "EXACT", "value": "foo"}}}

    assert response.has_errors is False, response
    assert len(response.edges) == 1
    assert response.node() == {"pk": example.pk}


def test_graphql__filter__user_defined__related_alias(graphql: GraphQLClient):
    example = ExampleFactory.create(name="foo", forward_one_to_one_field__name="bar")
    ExampleFactory.create(name="foobar")

    query = """
        query {
          examples(
            filter: {
              field: fotoName,
              operation: EXACT,
              value: "bar",
            }
          ) {
            edges {
              node {
                pk
              }
            }
          }
        }
    """

    graphql.login_with_superuser()
    response = graphql(query)

    assert response.has_errors is False, response
    assert len(response.edges) == 1
    assert response.node() == {"pk": example.pk}


def test_graphql__filter__user_defined__complex_filter(graphql: GraphQLClient):
    example = ExampleFactory.create(name="foo", number=10)
    ExampleFactory.create(name="foobar")

    query = """
        query {
          examples(
            filter: {
              operation: AND,
                operations: [
                  {
                    operation: OR,
                    operations: [
                      {
                        field: name,
                        operation: CONTAINS,
                        value: "foo",
                      },
                      {
                        field: email,
                        operation: CONTAINS,
                        value: "foo",
                      },
                    ],
                  },
                  {
                    operation: NOT,
                    operations: [
                      {
                        field: number,
                        operation: LT,
                        value: 10,
                      }
                    ]
                  },
                ],
              }
            ) {
              edges {
                node {
                  pk
                }
              }
            }
        }
    """

    graphql.login_with_superuser()

    fields = {}
    filters = {}

    def tracker(info: GQLInfo):
        nonlocal fields, filters
        fields = get_fields_from_info(info)
        filters = get_filters_from_info(info)
        return filters

    with patch("graphene_django_extensions.bases.get_filters_from_info", side_effect=tracker):
        response = graphql(query)

    assert fields == [{"examples": [{"edges": [{"node": ["pk"]}]}]}]
    assert filters == {
        "examples": {
            "filter": {
                "operation": "AND",
                "operations": [
                    {
                        "operation": "OR",
                        "operations": [
                            {"field": "name", "operation": "CONTAINS", "value": "foo"},
                            {"field": "email", "operation": "CONTAINS", "value": "foo"},
                        ],
                    },
                    {
                        "operation": "NOT",
                        "operations": [
                            {"field": "number", "operation": "LT", "value": "10"},
                        ],
                    },
                ],
            }
        }
    }

    assert response.has_errors is False, response
    assert len(response.edges) == 1
    assert response.node() == {"pk": example.pk}


def test_graphql__filter__list_field(graphql: GraphQLClient):
    example = ExampleFactory.create(name="foo", example_state=ExampleState.ACTIVE)
    ExampleFactory.create(name="foobar")

    query = build_query(
        "exampleItems",
        name=example.name,
        example_state=[ExampleState.ACTIVE, ExampleState.INACTIVE],
    )

    graphql.login_with_superuser()

    fields = {}
    filters = {}

    def tracker(info: GQLInfo):
        nonlocal fields, filters
        fields = get_fields_from_info(info)
        filters = get_filters_from_info(info)
        return filters

    with patch("graphene_django_extensions.bases.get_filters_from_info", side_effect=tracker):
        response = graphql(query)

    assert fields == [{"exampleItems": ["pk"]}]
    assert filters == {"exampleItems": {"exampleState": ["ACTIVE", "INACTIVE"], "name": "foo"}}

    assert response.has_errors is False, response
    assert len(response.first_query_object) == 1
    assert response.first_query_object[0] == {"pk": example.pk}


def test_graphql__filter__sub_filter(graphql: GraphQLClient):
    example_1 = ExampleFactory.create()
    example_2 = ExampleFactory.create()
    f1 = ForwardManyToManyFactory.create(name="foo")
    f2 = ForwardManyToManyFactory.create(name="bar")
    example_1.forward_many_to_many_fields.add(f1)
    example_2.forward_many_to_many_fields.add(f2)

    query = build_query(
        "exampleItems",
        fields="""
            pk
            forwardManyToManyFields {
                name
            }
        """,
        forward_many_to_many_fields__pk=[f1.pk],
    )
    graphql.login_with_superuser()

    fields = {}
    filters = {}

    def tracker(info: GQLInfo):
        nonlocal fields, filters
        fields = get_fields_from_info(info)
        filters = get_filters_from_info(info)
        return filters

    with patch("graphene_django_extensions.bases.get_filters_from_info", side_effect=tracker):
        response = graphql(query)

    assert fields == [{"exampleItems": ["pk", {"forwardManyToManyFields": ["name"]}]}]
    assert filters == {"exampleItems": {"forwardManyToManyFields": {"pk": ["1"]}}}

    assert response.has_errors is False, response
    assert len(response.first_query_object) == 2
    assert response.first_query_object[0] == {"forwardManyToManyFields": [{"name": "foo"}], "pk": example_1.pk}
    assert response.first_query_object[1] == {"forwardManyToManyFields": [], "pk": example_2.pk}
