import pytest

from graphene_django_extensions.testing import GraphQLClient, build_mutation
from tests.example.models import ExampleState
from tests.factories import ExampleFactory, ForwardManyToOneFactory

pytestmark = [
    pytest.mark.django_db,
]


def test_graphql__create__validation_error(graphql: GraphQLClient):
    mto = ForwardManyToOneFactory.create()
    input_data = {
        "name": "foo",
        "number": -1,
        "email": "foo@email.com",
        "exampleState": ExampleState.ACTIVE.value,
        "forwardOneToOneField": {
            "name": "Test",
        },
        "forwardManyToOneField": mto.pk,
    }

    mutation = build_mutation("createExample", "ExampleCreateMutation")
    graphql.login_with_superuser()
    response = graphql(mutation, input_data=input_data)

    assert response.error_message() == "Mutation was unsuccessful."
    assert response.field_error_messages("number") == ["Number must be positive."]
    assert response.errors == [
        {
            "message": "Mutation was unsuccessful.",
            "path": ["createExample"],
            "extensions": {
                "code": "MUTATION_VALIDATION_ERROR",
                "errors": [
                    {
                        "field": "number",
                        "message": "Number must be positive.",
                        "code": "invalid",
                    },
                ],
            },
            "locations": [{"line": 1, "column": 63}],
        }
    ]


def test_graphql__update__validation_error(graphql: GraphQLClient):
    example = ExampleFactory.create()

    input_data = {"pk": example.pk, "name": "foo", "number": -1}

    mutation = build_mutation("updateExample", "ExampleUpdateMutation")
    graphql.login_with_superuser()
    response = graphql(mutation, input_data=input_data)

    assert response.error_message() == "Mutation was unsuccessful."
    assert response.field_error_messages("number") == ["Number must be positive."]
    assert response.errors == [
        {
            "message": "Mutation was unsuccessful.",
            "path": ["updateExample"],
            "extensions": {
                "code": "MUTATION_VALIDATION_ERROR",
                "errors": [
                    {
                        "field": "number",
                        "message": "Number must be positive.",
                        "code": "invalid",
                    },
                ],
            },
            "locations": [{"line": 1, "column": 63}],
        }
    ]


def test_graphql__delete__validation_error(graphql: GraphQLClient):
    example = ExampleFactory.create(name="foo", number=-1)

    input_data = {"pk": example.pk}

    mutation = build_mutation("deleteExample", "ExampleDeleteMutation", fields="deleted")
    graphql.login_with_superuser()
    response = graphql(mutation, input_data=input_data)

    assert response.error_message() == "Mutation was unsuccessful."
    assert response.field_error_messages("number") == ["Number must be positive."]
    assert response.errors == [
        {
            "message": "Mutation was unsuccessful.",
            "path": ["deleteExample"],
            "extensions": {
                "code": "MUTATION_VALIDATION_ERROR",
                "errors": [
                    {
                        "field": "number",
                        "message": "Number must be positive.",
                        "code": "invalid",
                    },
                ],
            },
            "locations": [{"line": 1, "column": 63}],
        }
    ]
