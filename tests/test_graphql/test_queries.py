import pytest

from example_project.app.nodes import ExampleNode
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


def test_graphql__query__all_fields(graphql: GraphQLClient):
    example = ExampleFactory.create()

    fields = """
        pk
        name
        nameFi
        nameEn
        email
        exampleState
        duration
    """
    query = build_query("exampleItem", fields=fields)
    graphql.login_with_superuser()
    response = graphql(query)

    assert response.has_errors is False, response
    assert response.first_query_object == {
        "pk": example.pk,
        "name": example.name,
        "nameFi": example.name_fi,
        "nameEn": example.name_en,
        "email": example.email,
        "exampleState": example.example_state,
        "duration": int(example.duration.total_seconds()),
    }


def test_graphql__query__field(graphql: GraphQLClient):
    example = ExampleFactory.create()

    query = build_query("exampleItem")
    response = graphql(query)

    assert response.has_errors is False, response
    assert response.first_query_object == {"pk": example.pk}


def test_graphql__query__list(graphql: GraphQLClient):
    example_1 = ExampleFactory.create()
    example_2 = ExampleFactory.create()

    query = build_query("exampleItems")
    graphql.login_with_superuser()
    response = graphql(query)

    assert response.has_errors is False, response
    assert sorted(response.first_query_object, key=lambda x: x["pk"]) == [{"pk": example_1.pk}, {"pk": example_2.pk}]


def test_graphql__query__node(graphql: GraphQLClient):
    example = ExampleFactory.create()

    global_id = ExampleNode.get_global_id(example.pk)

    query = build_query("example", id=global_id)
    graphql.login_with_superuser()
    response = graphql(query)

    assert response.has_errors is False, response
    assert response.first_query_object == {"pk": example.pk}


def test_graphql__query__connection(graphql: GraphQLClient):
    example = ExampleFactory.create()

    query = build_query("examples", connection=True)

    graphql.login_with_superuser()
    response = graphql(query)

    assert response.has_errors is False, response
    assert len(response.edges) == 1
    assert response.node() == {"pk": example.pk}


def test_graphql__query__optimizer(graphql: GraphQLClient):
    example = ExampleFactory.create()

    fields = """
        pk
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
        "forwardOneToOneField": {
            "name": example.forward_one_to_one_field.name,
        },
        "forwardManyToOneField": {
            "name": example.forward_many_to_one_field.name,
        },
    }


def test_graphql__query__optimizer__all_relations(graphql: GraphQLClient):
    # settings.DEBUG = True
    example_1 = ExampleFactory.create(name="a_foo")
    e1_f1 = ForwardManyToManyFactory.create()
    e1_f2 = ForwardManyToManyFactory.create()
    example_1.forward_many_to_many_fields.add(e1_f1, e1_f2)

    e1_r1 = ReverseOneToOneFactory.create(example_field=example_1)
    e1_r2 = ReverseOneToManyFactory.create(example_field=example_1)
    e1_r22 = ReverseOneToManyFactory.create(example_field=example_1)
    e1_r3 = ReverseManyToManyFactory.create(example_fields=[example_1])
    e1_r33 = ReverseManyToManyFactory.create(example_fields=[example_1])

    example_2 = ExampleFactory.create(name="b_foo")
    e2_f1 = ForwardManyToManyFactory.create()
    e2_f2 = ForwardManyToManyFactory.create()
    example_2.forward_many_to_many_fields.add(e2_f1, e2_f2)

    e2_r1 = ReverseOneToOneFactory.create(example_field=example_2)
    e2_r2 = ReverseOneToManyFactory.create(example_field=example_2)
    e2_r22 = ReverseOneToManyFactory.create(example_field=example_2)
    e2_r3 = ReverseManyToManyFactory.create(example_fields=[example_2])
    e2_r33 = ReverseManyToManyFactory.create(example_fields=[example_2])

    fields = """
        pk
        forwardOneToOneField {
          name
        }
        forwardManyToOneField {
          name
        }
        forwardManyToManyFields {
          name
        }
        reverseOneToOneRel {
          name
        }
        reverseOneToManyRels {
          name
        }
        reverseManyToManyRels {
          edges {
            node {
              name
            }
          }
        }
    """
    query = build_query("examples", fields=fields, connection=True, order_by="nameEnAsc")

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
    assert len(response.edges) == 2
    assert response.node(0) == {
        "pk": example_1.pk,
        "forwardOneToOneField": {
            "name": example_1.forward_one_to_one_field.name,
        },
        "forwardManyToOneField": {
            "name": example_1.forward_many_to_one_field.name,
        },
        "forwardManyToManyFields": [
            {
                "name": e1_f1.name,
            },
            {
                "name": e1_f2.name,
            },
        ],
        "reverseOneToOneRel": {
            "name": e1_r1.name,
        },
        "reverseOneToManyRels": [
            {
                "name": e1_r2.name,
            },
            {
                "name": e1_r22.name,
            },
        ],
        "reverseManyToManyRels": {
            "edges": [
                {"node": {"name": e1_r3.name}},
                {"node": {"name": e1_r33.name}},
            ],
        },
    }
    assert response.node(1) == {
        "pk": example_2.pk,
        "forwardOneToOneField": {
            "name": example_2.forward_one_to_one_field.name,
        },
        "forwardManyToOneField": {
            "name": example_2.forward_many_to_one_field.name,
        },
        "forwardManyToManyFields": [
            {
                "name": e2_f1.name,
            },
            {
                "name": e2_f2.name,
            },
        ],
        "reverseOneToOneRel": {
            "name": e2_r1.name,
        },
        "reverseOneToManyRels": [
            {
                "name": e2_r2.name,
            },
            {
                "name": e2_r22.name,
            },
        ],
        "reverseManyToManyRels": {
            "edges": [
                {"node": {"name": e2_r3.name}},
                {"node": {"name": e2_r33.name}},
            ],
        },
    }


@pytest.mark.parametrize("experimental_translation_fields", ["types"], indirect=True)
def test_graphql__query__translations__accept_language(graphql: GraphQLClient, experimental_translation_fields):
    example = ExampleFactory.create(name_fi="foo")

    fields = """
        pk
        name
    """
    query = build_query("examples", fields=fields, connection=True)
    graphql.login_with_superuser()
    response = graphql(query, headers={"Accept-Language": "fi"})

    assert response.has_errors is False, response
    assert len(response.edges) == 1
    assert response.node(0) == {
        "pk": example.pk,
        "name": example.name_fi,
    }


@pytest.mark.parametrize("experimental_translation_fields", ["types"], indirect=True)
def test_graphql__query__translations__accept_language__null(graphql: GraphQLClient, experimental_translation_fields):
    example = ExampleFactory.create()
    assert example.name_fi is None

    fields = """
        pk
        name
    """
    query = build_query("examples", fields=fields, connection=True)
    graphql.login_with_superuser()
    response = graphql(query, headers={"Accept-Language": "fi"})

    assert response.has_errors is False, response
    assert len(response.edges) == 1
    assert response.node(0) == {
        "pk": example.pk,
        "name": "",  # empty, since field cannot be null
    }


@pytest.mark.parametrize("experimental_translation_fields", ["types"], indirect=True)
def test_graphql__query__translations__types(graphql: GraphQLClient, experimental_translation_fields):
    example = ExampleFactory.create()

    fields = """
        pk
        name
        nameTranslations { fi en }
    """
    query = build_query("examples", fields=fields, connection=True)
    graphql.login_with_superuser()
    response = graphql(query)

    assert response.has_errors is False, response
    assert len(response.edges) == 1
    assert response.node(0) == {
        "pk": example.pk,
        "name": example.name_en,
        "nameTranslations": {
            "fi": example.name_fi,
            "en": example.name_en,
        },
    }


@pytest.mark.parametrize("experimental_translation_fields", ["list"], indirect=True)
def test_graphql__query__translations__list(graphql: GraphQLClient, experimental_translation_fields):
    example = ExampleFactory.create()

    fields = """
        pk
        name
        nameTranslations { language value }
    """
    query = build_query("examples", fields=fields, connection=True)
    graphql.login_with_superuser()
    response = graphql(query)

    assert response.has_errors is False, response
    assert len(response.edges) == 1
    assert response.node(0) == {
        "pk": example.pk,
        "name": example.name_en,
        "nameTranslations": [
            {
                "language": "en",
                "value": example.name_en,
            },
            {
                "language": "fi",
                "value": example.name_fi,
            },
        ],
    }
