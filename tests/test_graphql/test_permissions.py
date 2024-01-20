import pytest

from graphene_django_extensions.testing import GraphQLClient, build_mutation, build_query
from tests.example.models import ExampleState
from tests.example.nodes import ExampleNode
from tests.factories import ExampleFactory, ForwardManyToOneFactory

pytestmark = [
    pytest.mark.django_db,
]


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


def test_graphql__create__permission_error(graphql: GraphQLClient):
    mto = ForwardManyToOneFactory.create()
    input_data = {
        "name": "foo",
        "number": 123,
        "email": "foo@email.com",
        "exampleState": ExampleState.ACTIVE.value,
        "forwardOneToOneField": {
            "name": "Test",
        },
        "forwardManyToOneField": mto.pk,
    }

    mutation = build_mutation("createExample", "ExampleCreateMutation")
    response = graphql(mutation, input_data=input_data)

    assert response.field_error_messages() == ["No permission to create."]


def test_graphql__update__permission_errors(graphql: GraphQLClient):
    example = ExampleFactory.create()

    input_data = {"pk": example.pk, "name": "foo"}
    mutation = build_mutation("updateExample", "ExampleUpdateMutation")
    response = graphql(mutation, input_data=input_data)

    assert response.field_error_messages() == ["No permission to update."]


def test_graphql__delete__permission_error(graphql: GraphQLClient):
    example = ExampleFactory.create(name="foo", number=1)

    input_data = {"pk": example.pk}
    mutation = build_mutation("deleteExample", "ExampleDeleteMutation", fields="deleted errors { messages field }")
    response = graphql(mutation, input_data=input_data)

    assert response.field_error_messages() == ["No permission to delete."]


def test_graphql__custom__permission_error(graphql: GraphQLClient):
    input_data = {"name": "foo"}
    mutation = build_mutation("customExample", "ExampleCustomMutation")
    response = graphql(mutation, input_data=input_data)

    assert response.field_error_messages() == ["No permission to mutate."]
