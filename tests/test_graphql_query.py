import pytest

from graphene_django_extensions.testing import GraphQLClient, build_query
from tests.example.models import ExampleState
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
    assert response.first_query_object == [
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


def test_graphql__query__all_relations(graphql: GraphQLClient):
    example = ExampleFactory.create()
    f1 = ForwardManyToManyFactory.create()
    example.forward_many_to_many_fields.add(f1)

    r1 = ReverseOneToOneFactory.create(example_field=example)
    r2 = ReverseOneToManyFactory.create(example_field=example)
    r3 = ReverseManyToManyFactory.create(example_fields=[example])

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
            ],
        },
        "reverseManyToManyRels": {
            "edges": [
                {
                    "node": {
                        "name": r3.name,
                    },
                },
            ],
        },
    }


def test_graphql__query__node__no_perms(graphql: GraphQLClient):
    example = ExampleFactory.create()

    global_id = ExampleNode.get_global_id(example.pk)
    query = build_query("example", fields="pk name", id=global_id)

    response = graphql(query)

    assert response.error_message("example") == "No permission to access node."


def test_graphql__query__connection__no_perms(graphql: GraphQLClient):
    ExampleFactory.create()

    query = build_query("examples", fields="pk name", connection=True)

    response = graphql(query)

    assert response.error_message("examples") == "No permission to access node."


def test_graphql__query__restricted_field__no_perms(graphql: GraphQLClient):
    ExampleFactory.create()

    query = build_query("examples", fields="pk email", connection=True)

    graphql.login_with_regular_user()
    response = graphql(query)

    assert response.error_message("email") == "No permission to access field."


def test_graphql__query__restricted_field__has_perms(graphql: GraphQLClient):
    ExampleFactory.create()
    graphql.login_with_superuser()

    query = build_query("examples", fields="pk email", connection=True)

    response = graphql(query)

    assert response.has_errors is False, response
    assert len(response.edges) == 1


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


def test_graphql__filter__relation(graphql: GraphQLClient, settings):
    # Test that filtering via a relation does not make an additional query
    # to fetch related items for checking whether the related objects exist.
    settings.DEBUG = True

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
    response = graphql(query)

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


def test_graphql__ordering__ascending(graphql: GraphQLClient):
    example_1 = ExampleFactory.create(name="foo2")
    example_2 = ExampleFactory.create(name="foo1")

    query = build_query("examples", connection=True, order_by="nameAsc")

    graphql.login_with_superuser()
    response = graphql(query)

    assert response.has_errors is False, response
    assert len(response.edges) == 2
    assert response.node(0) == {"pk": example_2.pk}
    assert response.node(1) == {"pk": example_1.pk}


def test_graphql__ordering__descending(graphql: GraphQLClient):
    example_1 = ExampleFactory.create(name="foo2")
    example_2 = ExampleFactory.create(name="foo1")

    query = build_query("examples", connection=True, order_by="nameDesc")

    graphql.login_with_superuser()
    response = graphql(query)

    assert response.has_errors is False, response
    assert len(response.edges) == 2
    assert response.node(0) == {"pk": example_1.pk}
    assert response.node(1) == {"pk": example_2.pk}


def test_graphql__ordering__multiple(graphql: GraphQLClient):
    example_1 = ExampleFactory.create(name="foo2", number=1)
    example_2 = ExampleFactory.create(name="foo1", number=2)

    query = build_query("examples", connection=True, order_by=["nameAsc", "numberDesc"])

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


def test_graphql__client_testing(graphql: GraphQLClient, settings):
    settings.DEBUG = True
    query = build_query("examples", fields="pk name", connection=True)
    graphql.login_with_superuser()
    response = graphql(query)

    assert str(response) == '{\n  "data": {\n    "examples": {\n      "edges": []\n    }\n  }\n}'
    assert repr(response) == "{'data': {'examples': {'edges': []}}}"
    assert len(response) == 0
    assert response["examples"] == {"edges": []}
    assert "examples" in response

    assert len(response.queries) == 3
    assert response.query_log != (
        "---------------------------------------------------------------------------\n"
        ">>> Queries (0):\n"
        "---------------------------------------------------------------------------"
    )
