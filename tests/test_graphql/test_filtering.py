from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from query_optimizer.selections import get_field_selections

from graphene_django_extensions.testing import GraphQLClient, build_query
from graphene_django_extensions.utils import get_filter_info
from tests.example.filtersets import ExampleFilterSet, ForwardManyToManyFilterSet
from tests.example.models import ExampleState
from tests.factories import ExampleFactory, ForwardManyToManyFactory

if TYPE_CHECKING:
    from django.db import models

    from graphene_django_extensions.typing import GQLInfo

pytestmark = [
    pytest.mark.django_db,
]


def test_graphql__filter(graphql: GraphQLClient):
    example = ExampleFactory.create(name="foo", example_state=ExampleState.ACTIVE)
    ExampleFactory.create(name="foobar")

    query = build_query(
        "examples",
        connection=True,
        name_en=example.name_en,
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

    query = build_query("examples", connection=True, order_by="nameEnAsc", one=example_1.number, two=example_2.number)

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
              field: nameEn,
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

    selections = []
    filters = {}

    def tracker(info: GQLInfo, model: type[models.Model]):
        nonlocal selections, filters
        if not selections:
            selections = get_field_selections(info, model)
        filters = get_filter_info(info, model)
        return filters

    with patch("query_optimizer.optimizer.get_filter_info", side_effect=tracker):
        response = graphql(query)

    assert selections == ["pk"]
    assert filters == {
        "name": "ExampleNodeConnection",
        "children": {},
        "filters": {
            "filter": {
                "field": "name_en",  # Actually enum nameEn, but has value name_en.
                "operation": "EXACT",
                "value": "foo",
            },
        },
        "filterset_class": ExampleFilterSet,
        "is_connection": True,
        "is_node": False,
        "max_limit": 100,
    }

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
                        field: nameEn,
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

    selections = []
    filters = {}

    def tracker(info: GQLInfo, model: type[models.Model]):
        nonlocal selections, filters
        if not selections:
            selections = get_field_selections(info, model)
        filters = get_filter_info(info, model)
        return filters

    with patch("query_optimizer.optimizer.get_filter_info", side_effect=tracker):
        response = graphql(query)

    assert selections == ["pk"]
    assert filters == {
        "name": "ExampleNodeConnection",
        "children": {},
        "filters": {
            "filter": {
                "field": None,
                "operation": "AND",
                "operations": [
                    {
                        "field": None,
                        "operation": "OR",
                        "operations": [
                            {
                                "field": "name_en",  # Actually enum nameEn, but has value name_en.
                                "operation": "CONTAINS",
                                "value": "foo",
                            },
                            {
                                "field": "email",
                                "operation": "CONTAINS",
                                "value": "foo",
                            },
                        ],
                    },
                    {
                        "field": None,
                        "operation": "NOT",
                        "operations": [
                            {
                                "field": "number",
                                "operation": "LT",
                                "value": 10,
                            },
                        ],
                    },
                ],
            }
        },
        "filterset_class": ExampleFilterSet,
        "is_connection": True,
        "is_node": False,
        "max_limit": 100,
    }

    assert response.has_errors is False, response
    assert len(response.edges) == 1
    assert response.node() == {"pk": example.pk}


def test_graphql__filter__list_field(graphql: GraphQLClient):
    example = ExampleFactory.create(name="foo", example_state=ExampleState.ACTIVE)
    ExampleFactory.create(name="foobar")

    query = build_query(
        "exampleItems",
        name_en=example.name_en,
        example_state=[ExampleState.ACTIVE, ExampleState.INACTIVE],
    )

    graphql.login_with_superuser()

    selections = []
    filters = {}

    def tracker(info: GQLInfo, model: type[models.Model]):
        nonlocal selections, filters
        if not selections:
            selections = get_field_selections(info, model)
        filters = get_filter_info(info, model)
        return filters

    with patch("query_optimizer.optimizer.get_filter_info", side_effect=tracker):
        response = graphql(query)

    assert selections == ["pk"]
    assert filters == {
        "name": "ExampleNode",
        "children": {},
        "filters": {
            "example_state": [ExampleState.ACTIVE, ExampleState.INACTIVE],
            "name_en": "foo",
        },
        "filterset_class": ExampleFilterSet,
        "is_connection": False,
        "is_node": False,
        "max_limit": 100,
    }

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

    selections = []
    filters = {}

    def tracker(info: GQLInfo, model: type[models.Model]):
        nonlocal selections, filters
        if not selections:
            selections = get_field_selections(info, model)
        filters = get_filter_info(info, model)
        return filters

    with patch("query_optimizer.optimizer.get_filter_info", side_effect=tracker):
        response = graphql(query)

    assert selections == [
        "pk",
        {
            "forward_many_to_many_fields": ["name"],
        },
    ]
    assert filters == {
        "name": "ExampleNode",
        "filters": {},
        "filterset_class": ExampleFilterSet,
        "is_connection": False,
        "is_node": False,
        "max_limit": 100,
        "children": {
            "forward_many_to_many_fields": {
                "name": "ForwardManyToManyNode",
                "filters": {"pk": [1]},
                "filterset_class": ForwardManyToManyFilterSet,
                "is_connection": False,
                "is_node": False,
                "max_limit": 100,
                "children": {},
            }
        },
    }

    assert response.has_errors is False, response
    assert len(response.first_query_object) == 2
    assert response.first_query_object[0] == {"forwardManyToManyFields": [{"name": "foo"}], "pk": example_1.pk}
    assert response.first_query_object[1] == {"forwardManyToManyFields": [], "pk": example_2.pk}
