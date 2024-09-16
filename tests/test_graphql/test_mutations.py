import datetime

import pytest

from example_project.app.models import Example, ExampleState
from graphene_django_extensions.testing import GraphQLClient, build_mutation
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
        "duration": int(datetime.timedelta(seconds=900).total_seconds()),
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
        "duration": int(datetime.timedelta(seconds=900).total_seconds()),
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


def test_graphql__update__does_not_exist(graphql: GraphQLClient):
    ExampleFactory.create(name="foo", number=1)
    input_data = {"pk": 0}

    mutation = build_mutation("updateExample", "ExampleUpdateMutation", fields="pk")
    graphql.login_with_superuser()
    response = graphql(mutation, input_data=input_data)

    assert response.error_code() == "NOT_FOUND"
    assert response.error_message() == "`Example` object matching query `{'pk': 0}` does not exist."


def test_graphql__delete__does_not_exist(graphql: GraphQLClient):
    ExampleFactory.create(name="foo", number=1)
    input_data = {"pk": 0}

    mutation = build_mutation("deleteExample", "ExampleDeleteMutation", fields="deleted")
    graphql.login_with_superuser()
    response = graphql(mutation, input_data=input_data)

    assert response.error_code() == "NOT_FOUND"
    assert response.error_message() == "`Example` object matching query `{'pk': '0'}` does not exist."


def test_graphql__file(graphql, mock_png):
    data = {"image": mock_png}
    mutation = build_mutation("imageMutation", "ImageMutation", fields="name success")
    response = graphql(mutation, input_data=data)

    assert response.has_errors is False
    assert response.first_query_object == {"name": "image.png", "success": True}


def test_graphql__schema_errors(graphql: GraphQLClient):
    mutation = build_mutation("createExample", "ExampleCreateMutation", fields="name")

    graphql.login_with_superuser()
    response = graphql(mutation, input_data={})

    assert response.has_schema_errors is True, response
