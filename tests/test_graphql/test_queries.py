import pytest

from graphene_django_extensions.testing import GraphQLClient, build_query
from tests.example.nodes import ExampleNode
from tests.factories import (
    ExampleFactory,
    ForwardManyToManyFactory,
    ReverseManyToManyFactory,
    ReverseOneToManyFactory,
    ReverseOneToOneFactory,
)

pytestmark = [
    pytest.mark.django_db,
]


def test_graphql__query__field(graphql: GraphQLClient):
    example = ExampleFactory.create()

    query = build_query("exampleItem", fields="pk name")
    response = graphql(query)

    assert response.has_errors is False, response
    assert response.first_query_object == {"pk": example.pk, "name": example.name}


def test_graphql__query__list(graphql: GraphQLClient):
    example_1 = ExampleFactory.create()
    example_2 = ExampleFactory.create()

    query = build_query("exampleItems", fields="pk name")
    graphql.login_with_superuser()
    response = graphql(query)

    assert response.has_errors is False, response
    assert sorted(response.first_query_object, key=lambda x: x["pk"]) == [
        {"pk": example_1.pk, "name": example_1.name},
        {"pk": example_2.pk, "name": example_2.name},
    ]


def test_graphql__query__node(graphql: GraphQLClient):
    example = ExampleFactory.create()

    global_id = ExampleNode.get_global_id(example.pk)

    query = build_query("example", fields="pk name", id=global_id)
    graphql.login_with_superuser()
    response = graphql(query)

    assert response.has_errors is False, response
    assert response.first_query_object == {"pk": example.pk, "name": example.name}


def test_graphql__query__connection(graphql: GraphQLClient):
    example = ExampleFactory.create()

    query = build_query("examples", fields="pk name", connection=True)

    graphql.login_with_superuser()
    response = graphql(query)

    assert response.has_errors is False, response
    assert len(response.edges) == 1
    assert response.node() == {"pk": example.pk, "name": example.name}


def test_graphql__query__optimizer(graphql: GraphQLClient, settings):
    settings.DEBUG = True
    example = ExampleFactory.create()

    fields = """
        pk
        name
        forwardOneToOneField {
          name
        }
        forwardManyToOneField {
          name
        }
    """
    query = build_query("examples", fields=fields, connection=True)

    graphql.login_with_superuser()
    response = graphql(query)

    # 1) Get session
    # 2) Get user
    # 3) Count examples for pagination
    # 4) Fetch examples, forward_one_to_one, and forward_many_to_one
    response.assert_query_count(4)

    assert response.has_errors is False, response
    assert len(response.edges) == 1
    assert response.node() == {
        "pk": example.pk,
        "name": example.name,
        "forwardOneToOneField": {
            "name": example.forward_one_to_one_field.name,
        },
        "forwardManyToOneField": {
            "name": example.forward_many_to_one_field.name,
        },
    }


def test_graphql__query__optimizer__all_relations(graphql: GraphQLClient, settings):
    settings.DEBUG = True
    example = ExampleFactory.create()
    f1 = ForwardManyToManyFactory.create()
    f2 = ForwardManyToManyFactory.create()
    example.forward_many_to_many_fields.add(f1, f2)

    r1 = ReverseOneToOneFactory.create(example_field=example)
    r2 = ReverseOneToManyFactory.create(example_field=example)
    r22 = ReverseOneToManyFactory.create(example_field=example)
    r3 = ReverseManyToManyFactory.create(example_fields=[example])
    r33 = ReverseManyToManyFactory.create(example_fields=[example])

    fields = """
        pk
        name
        forwardOneToOneField {
          name
        }
        forwardManyToOneField {
          name
        }
        forwardManyToManyFields {
          edges {
            node {
              name
            }
          }
        }
        reverseOneToOneRel {
          name
        }
        reverseOneToManyRels {
          edges {
            node {
              name
            }
          }
        }
        reverseManyToManyRels {
          edges {
            node {
              name
            }
          }
        }
    """
    query = build_query("examples", fields=fields, connection=True)

    graphql.login_with_superuser()
    response = graphql(query)

    # 1) Get session
    # 2) Get user
    # 3) Count examples for pagination
    # 4) Fetch examples, forward_one_to_one, forward_many_to_one, and reverse_one_to_one
    # 5) Fetch forward_many_to_many
    # 6) Fetch reverse_one_to_many
    # 7) Fetch reverse_many_to_many
    response.assert_query_count(7)

    assert response.has_errors is False, response
    assert len(response.edges) == 1
    assert response.node() == {
        "pk": example.pk,
        "name": example.name,
        "forwardOneToOneField": {
            "name": example.forward_one_to_one_field.name,
        },
        "forwardManyToOneField": {
            "name": example.forward_many_to_one_field.name,
        },
        "forwardManyToManyFields": {
            "edges": [
                {
                    "node": {
                        "name": f1.name,
                    },
                },
                {
                    "node": {
                        "name": f2.name,
                    },
                },
            ],
        },
        "reverseOneToOneRel": {
            "name": r1.name,
        },
        "reverseOneToManyRels": {
            "edges": [
                {
                    "node": {
                        "name": r2.name,
                    },
                },
                {
                    "node": {
                        "name": r22.name,
                    },
                },
            ],
        },
        "reverseManyToManyRels": {
            "edges": [
                {
                    "node": {
                        "name": r3.name,
                    },
                },
                {
                    "node": {
                        "name": r33.name,
                    },
                },
            ],
        },
    }
