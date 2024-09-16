import datetime

import pytest

from example_project.app.models import ExampleState
from example_project.app.nodes import ExampleNode
from graphene_django_extensions.testing import GraphQLClient, build_mutation, build_query
from tests.factories import ExampleFactory, ForwardManyToOneFactory

pytestmark = [
    pytest.mark.django_db,
]


def test_graphql__query__node__no_perms(graphql: GraphQLClient):
    example = ExampleFactory.create()

    global_id = ExampleNode.get_global_id(example.pk)
    query = build_query("example", id=global_id)

    response = graphql(query)

    assert response.error_message("example") == "No permission to access node."
    assert response.errors == [
        {
            "message": "No permission to access node.",
            "path": ["example"],
            "extensions": {"code": "NODE_PERMISSION_DENIED"},
            "locations": [{"column": 9, "line": 1}],
        },
    ]


def test_graphql__query__list_field__no_perms(graphql: GraphQLClient):
    ExampleFactory.create()

    query = build_query("exampleItems")

    response = graphql(query)

    assert response.error_message("exampleItems") == "No permission to access node."
    assert response.errors == [
        {
            "message": "No permission to access node.",
            "path": ["exampleItems"],
            "extensions": {"code": "FILTER_PERMISSION_DENIED"},
            "locations": [{"column": 9, "line": 1}],
        },
    ]


def test_graphql__query__connection__no_perms(graphql: GraphQLClient):
    ExampleFactory.create()

    query = build_query("examples", connection=True)

    response = graphql(query)

    assert response.error_message("examples") == "No permission to access node."
    assert response.errors == [
        {
            "message": "No permission to access node.",
            "path": ["examples"],
            "extensions": {"code": "FILTER_PERMISSION_DENIED"},
            "locations": [{"column": 9, "line": 1}],
        },
    ]


def test_graphql__query__restricted_field__no_perms(graphql: GraphQLClient):
    ExampleFactory.create()

    query = build_query("examples", fields="pk email", connection=True)

    graphql.login_with_regular_user()
    response = graphql(query)

    assert response.error_message("email") == "No permission to access field."
    assert response.errors == [
        {
            "message": "No permission to access field.",
            "path": ["examples", "edges", 0, "node", "email"],
            "extensions": {"code": "FIELD_PERMISSION_DENIED"},
            "locations": [{"column": 38, "line": 1}],
        },
    ]


def test_graphql__query__restricted_field__has_perms(graphql: GraphQLClient):
    ExampleFactory.create()
    graphql.login_with_superuser()

    query = build_query("examples", fields="pk email", connection=True)

    response = graphql(query)

    assert response.has_errors is False, response
    assert len(response.edges) == 1


def test_graphql__create__permission_error(graphql: GraphQLClient):
    mto = ForwardManyToOneFactory.create()
    input_data = {
        "name": "foo",
        "number": 123,
        "email": "foo@email.com",
        "exampleState": ExampleState.ACTIVE.value,
        "duration": int(datetime.timedelta(seconds=900).total_seconds()),
        "forwardOneToOneField": {
            "name": "Test",
        },
        "forwardManyToOneField": mto.pk,
    }

    mutation = build_mutation("createExample", "ExampleCreateMutation")
    response = graphql(mutation, input_data=input_data)

    assert response.error_message("createExample") == "No permission to create."
    assert response.errors == [
        {
            "message": "No permission to create.",
            "path": ["createExample"],
            "extensions": {"code": "CREATE_PERMISSION_DENIED"},
            "locations": [{"column": 63, "line": 1}],
        },
    ]


def test_graphql__update__permission_errors(graphql: GraphQLClient):
    example = ExampleFactory.create()

    input_data = {"pk": example.pk, "name": "foo"}
    mutation = build_mutation("updateExample", "ExampleUpdateMutation")
    response = graphql(mutation, input_data=input_data)

    assert response.error_message("updateExample") == "No permission to update."
    assert response.errors == [
        {
            "message": "No permission to update.",
            "path": ["updateExample"],
            "extensions": {"code": "UPDATE_PERMISSION_DENIED"},
            "locations": [{"column": 63, "line": 1}],
        },
    ]


def test_graphql__delete__permission_error(graphql: GraphQLClient):
    example = ExampleFactory.create(name="foo", number=1)

    input_data = {"pk": example.pk}
    mutation = build_mutation("deleteExample", "ExampleDeleteMutation", fields="deleted")
    response = graphql(mutation, input_data=input_data)

    assert response.error_message("deleteExample") == "No permission to delete."
    assert response.errors == [
        {
            "message": "No permission to delete.",
            "path": ["deleteExample"],
            "extensions": {"code": "DELETE_PERMISSION_DENIED"},
            "locations": [{"column": 63, "line": 1}],
        },
    ]


def test_graphql__custom__permission_error(graphql: GraphQLClient):
    input_data = {"name": "foo"}
    mutation = build_mutation("customExample", "ExampleCustomMutation")
    response = graphql(mutation, input_data=input_data)

    assert response.error_message("customExample") == "No permission to mutate."
    assert response.errors == [
        {
            "message": "No permission to mutate.",
            "path": ["customExample"],
            "extensions": {"code": "MUTATION_PERMISSION_DENIED"},
            "locations": [{"column": 63, "line": 1}],
        },
    ]
