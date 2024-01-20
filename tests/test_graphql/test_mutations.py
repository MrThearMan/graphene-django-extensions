import pytest

from graphene_django_extensions.testing import GraphQLClient, build_mutation
from tests.example.models import Example, ExampleState
from tests.factories import ExampleFactory, ForwardManyToOneFactory, ForwardOneToOneFactory

pytestmark = [
    pytest.mark.django_db,
]


def test_graphql__create(graphql: GraphQLClient):
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


def test_graphql__update(graphql: GraphQLClient):
    example = ExampleFactory.create(name="foo", number=1)

    mto = ForwardManyToOneFactory.create()
    input_data = {
        "pk": example.pk,
        "name": "foo",
        "number": 123,
        "email": "foo@email.com",
        "exampleState": ExampleState.ACTIVE.value,
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


def test_graphql__delete(graphql: GraphQLClient):
    example = ExampleFactory.create(name="foo", number=1)

    input_data = {"pk": example.pk}
    mutation = build_mutation("deleteExample", "ExampleDeleteMutation", fields="deleted")

    graphql.login_with_superuser()
    response = graphql(mutation, input_data=input_data)

    assert response.has_errors is False, response
    assert response.first_query_object == {
        "deleted": True,
    }


def test_graphql__custom(graphql: GraphQLClient):
    input_data = {"name": "foo"}
    mutation = build_mutation("customExample", "ExampleCustomMutation")

    graphql.login_with_superuser()
    response = graphql(mutation, input_data=input_data)
    example = Example.objects.first()

    assert response.has_errors is False, response
    assert response.first_query_object == {
        "pk": example.pk,
    }


def test_graphql__form(graphql: GraphQLClient):
    oto = ForwardOneToOneFactory.create()
    mto = ForwardManyToOneFactory.create()
    input_data = {
        "name": "foo",
        "number": 123,
        "email": "foo@email.com",
        "exampleState": ExampleState.ACTIVE.value,
        "forwardOneToOneField": oto.pk,
        "forwardManyToOneField": mto.pk,
    }

    fields = "name number email forwardOneToOneField forwardManyToOneField"
    mutation = build_mutation("formMutation", "ExampleFormMutation", fields=fields)

    graphql.login_with_superuser()
    response = graphql(mutation, input_data=input_data)

    assert response.has_errors is False, response
    assert response.first_query_object == {
        "name": "foo",
        "number": 123,
        "email": "foo@email.com",
        "forwardOneToOneField": str(oto),
        "forwardManyToOneField": str(mto),
    }


def test_graphql__form__custom(graphql: GraphQLClient):
    input_data = {"name": "foo"}
    mutation = build_mutation("formCustomMutation", "ExampleFormCustomMutation")

    graphql.login_with_superuser()
    response = graphql(mutation, input_data=input_data)
    example = Example.objects.first()

    assert response.has_errors is False, response
    assert response.first_query_object == {
        "pk": example.pk,
    }
