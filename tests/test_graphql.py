import pytest

from graphene_django_extensions.testing import GraphQLClient, build_mutation, build_query
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


def test_graphql__filter(graphql: GraphQLClient):
    example = ExampleFactory.create(name="foo")
    ExampleFactory.create(name="foobar")

    query = build_query("examples", connection=True, name=example.name)

    response = graphql(query)

    assert response.has_errors is False, response
    assert len(response.edges) == 1
    assert response.node() == {"pk": example.pk}


def test_graphql__ordering(graphql: GraphQLClient):
    example_1 = ExampleFactory.create(name="foo2")
    example_2 = ExampleFactory.create(name="foo1")

    query = build_query("examples", connection=True, order_by="name")

    response = graphql(query)

    assert response.has_errors is False, response
    assert len(response.edges) == 2
    assert response.node(0) == {"pk": example_2.pk}
    assert response.node(1) == {"pk": example_1.pk}


def test_graphql__ordering__custom_function(graphql: GraphQLClient):
    example_1 = ExampleFactory.create(number=2)
    example_2 = ExampleFactory.create(number=1)

    query = build_query("examples", connection=True, order_by="number")

    response = graphql(query)

    assert response.has_errors is False, response
    assert len(response.edges) == 2
    assert response.node(0) == {"pk": example_2.pk}
    assert response.node(1) == {"pk": example_1.pk}


def test_graphql__create(graphql: GraphQLClient):
    input_data = {
        "name": "foo",
        "number": 123,
        "email": "foo@email.com",
        "forwardOneToOneField": {
            "name": "Test",
        },
        "forwardManyToOneField": {
            "name": "Test",
        },
    }

    fields = "name number email forwardOneToOneField { name } forwardManyToOneField { name }"
    mutation = build_mutation("createExample", "ExampleCreateMutation", fields=fields)

    response = graphql(mutation, input_data=input_data)

    assert response.has_errors is False, response
    assert response.json == {
        "data": {
            "createExample": {
                "name": "foo",
                "number": 123,
                "email": "foo@email.com",
                "forwardManyToOneField": {"name": "Test"},
                "forwardOneToOneField": {"name": "Test"},
            }
        }
    }


def test_graphql__update(graphql: GraphQLClient):
    example = ExampleFactory.create(name="foo", number=1)

    input_data = {
        "pk": example.pk,
        "name": "foo",
        "number": 123,
        "email": "foo@email.com",
        "forwardOneToOneField": {
            "pk": example.forward_one_to_one_field.pk,
            "name": "Test",
        },
        "forwardManyToOneField": {
            "name": "Test",
        },
    }

    fields = "pk name number email forwardOneToOneField { name } forwardManyToOneField { name }"
    mutation = build_mutation("updateExample", "ExampleUpdateMutation", fields=fields)

    response = graphql(mutation, input_data=input_data)

    assert response.has_errors is False, response
    assert response.json == {
        "data": {
            "updateExample": {
                "pk": example.pk,
                "name": "foo",
                "number": 123,
                "email": "foo@email.com",
                "forwardManyToOneField": {"name": "Test"},
                "forwardOneToOneField": {"name": "Test"},
            }
        }
    }


def test_graphql__delete(graphql: GraphQLClient):
    example = ExampleFactory.create(name="foo", number=1)

    input_data = {
        "pk": example.pk,
    }

    fields = "deleted"
    mutation = build_mutation("deleteExample", "ExampleDeleteMutation", fields=fields)

    response = graphql(mutation, input_data=input_data)

    assert response.has_errors is False, response
    assert response.json == {
        "data": {
            "deleteExample": {
                "deleted": True,
            }
        }
    }
