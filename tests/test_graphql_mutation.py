import pytest

from graphene_django_extensions.testing import GraphQLClient, build_mutation
from tests.example.models import Example, State
from tests.factories import ExampleFactory, ForwardManyToOneFactory

pytestmark = [
    pytest.mark.django_db,
]


def test_graphql__create(graphql: GraphQLClient, query_counter):
    mto = ForwardManyToOneFactory.create()
    input_data = {
        "name": "foo",
        "number": 123,
        "email": "foo@email.com",
        "state": State.ACTIVE.value,
        "forwardOneToOneField": {
            "name": "Test",
        },
        "forwardManyToOneField": mto.pk,
    }

    fields = "name number email forwardOneToOneField { name } forwardManyToOneField"
    mutation = build_mutation("createExample", "ExampleCreateMutation", fields=fields)

    graphql.login_with_superuser()
    response = graphql(mutation, input_data=input_data)

    assert response.has_errors is False, response
    assert response.first_query_object == {
        "name": "foo",
        "number": 123,
        "email": "foo@email.com",
        "forwardOneToOneField": {"name": "Test"},
        "forwardManyToOneField": mto.pk,
    }


def test_graphql__create__validation_error(graphql: GraphQLClient):
    mto = ForwardManyToOneFactory.create()
    input_data = {
        "name": "foo",
        "number": -1,
        "email": "foo@email.com",
        "state": State.ACTIVE.value,
        "forwardOneToOneField": {
            "name": "Test",
        },
        "forwardManyToOneField": mto.pk,
    }

    mutation = build_mutation("createExample", "ExampleCreateMutation")
    graphql.login_with_superuser()
    response = graphql(mutation, input_data=input_data)

    assert response.field_error_messages("number") == ["Number must be positive."]


def test_graphql__create__permission_error(graphql: GraphQLClient):
    mto = ForwardManyToOneFactory.create()
    input_data = {
        "name": "foo",
        "number": 123,
        "email": "foo@email.com",
        "state": State.ACTIVE.value,
        "forwardOneToOneField": {
            "name": "Test",
        },
        "forwardManyToOneField": mto.pk,
    }

    mutation = build_mutation("createExample", "ExampleCreateMutation")
    response = graphql(mutation, input_data=input_data)

    assert response.field_error_messages() == ["No permission to create."]


def test_graphql__update(graphql: GraphQLClient):
    example = ExampleFactory.create(name="foo", number=1)

    mto = ForwardManyToOneFactory.create()
    input_data = {
        "pk": example.pk,
        "name": "foo",
        "number": 123,
        "email": "foo@email.com",
        "state": State.ACTIVE.value,
        "forwardOneToOneField": {
            "pk": example.forward_one_to_one_field.pk,
            "name": "Test",
        },
        "forwardManyToOneField": mto.pk,
    }

    fields = "pk name number email forwardOneToOneField { name } forwardManyToOneField"
    mutation = build_mutation("updateExample", "ExampleUpdateMutation", fields=fields)

    graphql.login_with_superuser()
    response = graphql(mutation, input_data=input_data)

    assert response.has_errors is False, response
    assert response.first_query_object == {
        "pk": example.pk,
        "name": "foo",
        "number": 123,
        "email": "foo@email.com",
        "forwardOneToOneField": {"name": "Test"},
        "forwardManyToOneField": mto.pk,
    }


def test_graphql__update__validation_error(graphql: GraphQLClient):
    example = ExampleFactory.create()

    input_data = {"pk": example.pk, "name": "foo", "number": -1}

    mutation = build_mutation("updateExample", "ExampleUpdateMutation")
    graphql.login_with_superuser()
    response = graphql(mutation, input_data=input_data)

    assert response.field_error_messages("number") == ["Number must be positive."]


def test_graphql__update__permission_errors(graphql: GraphQLClient):
    example = ExampleFactory.create()

    input_data = {"pk": example.pk, "name": "foo"}
    mutation = build_mutation("updateExample", "ExampleUpdateMutation")
    response = graphql(mutation, input_data=input_data)

    assert response.field_error_messages() == ["No permission to update."]


def test_graphql__delete(graphql: GraphQLClient):
    example = ExampleFactory.create(name="foo", number=1)

    input_data = {"pk": example.pk}
    mutation = build_mutation("deleteExample", "ExampleDeleteMutation", fields="deleted")

    graphql.login_with_superuser()
    response = graphql(mutation, input_data=input_data)

    assert response.has_errors is False, response
    assert response.first_query_object == {"deleted": True}


def test_graphql__delete__validation_error(graphql: GraphQLClient):
    example = ExampleFactory.create(name="foo", number=-1)

    input_data = {"pk": example.pk}

    mutation = build_mutation("deleteExample", "ExampleDeleteMutation", fields="deleted errors { messages field }")
    graphql.login_with_superuser()
    response = graphql(mutation, input_data=input_data)

    assert response.field_error_messages() == ["Number must be positive."]


def test_graphql__delete__permission_error(graphql: GraphQLClient):
    example = ExampleFactory.create(name="foo", number=1)

    input_data = {"pk": example.pk}
    mutation = build_mutation("deleteExample", "ExampleDeleteMutation", fields="deleted errors { messages field }")
    response = graphql(mutation, input_data=input_data)

    assert response.field_error_messages() == ["No permission to delete."]


def test_graphql__custom(graphql: GraphQLClient):
    input_data = {"name": "foo"}
    mutation = build_mutation("customExample", "ExampleCustomMutation", fields="pk")

    graphql.login_with_superuser()
    response = graphql(mutation, input_data=input_data)
    example = Example.objects.first()

    assert response.has_errors is False, response
    assert response.first_query_object == {"pk": str(example.pk)}


def test_graphql__custom__permission_error(graphql: GraphQLClient):
    input_data = {"name": "foo"}
    mutation = build_mutation("customExample", "ExampleCustomMutation", fields="pk errors { messages field }")
    response = graphql(mutation, input_data=input_data)

    assert response.field_error_messages() == ["No permission to mutate."]
