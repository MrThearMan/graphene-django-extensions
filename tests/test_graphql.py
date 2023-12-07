import pytest

from graphene_django_extensions.testing import GraphQLClient, build_query
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


def test_graphql__all_relations(graphql: GraphQLClient):
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
