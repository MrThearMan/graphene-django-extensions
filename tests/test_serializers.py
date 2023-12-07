import re
from copy import deepcopy
from typing import Any

import pytest
from django.contrib.auth.models import User
from django.db.models import NOT_PROVIDED
from django.http import HttpRequest
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request

from graphene_django_extensions.converters import convert_serializer_fields_to_not_required
from graphene_django_extensions.serializers import NestingModelSerializer
from tests.example.models import (
    Example,
    ForwardManyToMany,
    ForwardManyToOne,
    ForwardOneToOne,
    ReverseManyToMany,
    ReverseOneToMany,
    ReverseOneToOne,
)
from tests.factories import ExampleFactory

pytestmark = [
    pytest.mark.django_db,
]


class ForwardOneToOneSerializer(NestingModelSerializer):
    class Meta:
        model = ForwardOneToOne
        fields = ["pk", "name"]


class ForwardManyToManySerializer(NestingModelSerializer):
    class Meta:
        model = ForwardManyToMany
        fields = [
            "pk",
            "name",
        ]


class ForwardManyToOneSerializer(NestingModelSerializer):
    class Meta:
        model = ForwardManyToOne
        fields = [
            "pk",
            "name",
        ]


class ReverseOneToOneSerializer(NestingModelSerializer):
    class Meta:
        model = ReverseOneToOne
        fields = [
            "pk",
            "name",
        ]


class ReverseManyToManySerializer(NestingModelSerializer):
    class Meta:
        model = ReverseManyToMany
        fields = [
            "pk",
            "name",
        ]


class ReverseOneToManySerializer(NestingModelSerializer):
    class Meta:
        model = ReverseOneToMany
        fields = [
            "pk",
            "name",
        ]


class ExampleSerializer(NestingModelSerializer):
    forward_one_to_one_field = ForwardOneToOneSerializer()
    forward_many_to_one_field = ForwardManyToOneSerializer()
    forward_many_to_many_fields = ForwardManyToManySerializer(many=True)
    reverse_one_to_one_rel = ReverseOneToOneSerializer()
    reverse_one_to_many_rels = ReverseOneToManySerializer(many=True)
    reverse_many_to_many_rels = ReverseManyToManySerializer(many=True)

    class Meta:
        model = Example
        fields = [
            "pk",
            "name",
            "number",
            "email",
            "forward_one_to_one_field",
            "forward_many_to_one_field",
            "forward_many_to_many_fields",
            "reverse_one_to_one_rel",
            "reverse_one_to_many_rels",
            "reverse_many_to_many_rels",
        ]


EXAMPLE_DATA: dict[str, Any] = {
    "name": "foo",
    "number": 1,
    "email": "foofoo@email.com",
    "forward_one_to_one_field": {
        "name": "one",
    },
    "forward_many_to_one_field": {
        "name": "two",
    },
    "forward_many_to_many_fields": [
        {
            "name": "three",
        },
    ],
    "reverse_one_to_one_rel": {
        "name": "four",
    },
    "reverse_one_to_many_rels": [
        {
            "name": "five",
        },
    ],
    "reverse_many_to_many_rels": [
        {
            "name": "six",
        },
    ],
}


def test_nesting_model_serializer__create():
    serializer = ExampleSerializer(data=EXAMPLE_DATA)
    assert serializer.is_valid(raise_exception=True)
    serializer.save()

    examples: list[Example] = list(Example.objects.all())
    assert len(examples) == 1

    items_1: list[ForwardManyToMany] = list(examples[0].forward_many_to_many_fields.all())
    items_2: list[ReverseOneToMany] = list(examples[0].reverse_one_to_many_rels.all())
    items_3: list[ReverseManyToMany] = list(examples[0].reverse_many_to_many_rels.all())

    assert len(items_1) == 1
    assert len(items_2) == 1
    assert len(items_3) == 1

    assert examples[0].name == "foo"

    # Forward relations
    assert examples[0].forward_one_to_one_field.name == "one"
    assert examples[0].forward_many_to_one_field.name == "two"
    assert items_1[0].name == "three"

    # Reverse relations
    assert examples[0].reverse_one_to_one_rel.name == "four"
    assert items_2[0].name == "five"
    assert items_3[0].name == "six"


def test_nesting_model_serializer__update():
    example = ExampleFactory.create()
    oto_pk = example.forward_one_to_one_field.pk
    mto_pk = example.forward_many_to_one_field.pk
    mto_name = example.forward_many_to_one_field.name

    update_data = deepcopy(EXAMPLE_DATA)
    update_data["pk"] = example.pk
    update_data["forward_one_to_one_field"]["pk"] = oto_pk
    update_data["forward_many_to_one_field"] = {"pk": example.forward_many_to_one_field.pk}

    update_serializer = convert_serializer_fields_to_not_required(ExampleSerializer, lookup_field="pk")

    serializer = update_serializer(instance=example, data=update_data)
    assert serializer.is_valid(raise_exception=True)
    serializer.save()

    examples: list[Example] = list(Example.objects.all())
    assert len(examples) == 1

    items_1: list[ForwardManyToMany] = list(examples[0].forward_many_to_many_fields.all())
    items_2: list[ReverseOneToMany] = list(examples[0].reverse_one_to_many_rels.all())
    items_3: list[ReverseManyToMany] = list(examples[0].reverse_many_to_many_rels.all())

    assert len(items_1) == 1
    assert len(items_2) == 1
    assert len(items_3) == 1

    assert examples[0].name == EXAMPLE_DATA["name"]

    # Forward relations
    assert examples[0].forward_one_to_one_field.pk == oto_pk
    assert examples[0].forward_one_to_one_field.name == EXAMPLE_DATA["forward_one_to_one_field"]["name"]
    assert examples[0].forward_many_to_one_field.pk == mto_pk
    assert examples[0].forward_many_to_one_field.name == mto_name
    assert items_1[0].name == EXAMPLE_DATA["forward_many_to_many_fields"][0]["name"]

    # Reverse relations
    assert examples[0].reverse_one_to_one_rel.name == EXAMPLE_DATA["reverse_one_to_one_rel"]["name"]
    assert items_2[0].name == EXAMPLE_DATA["reverse_one_to_many_rels"][0]["name"]
    assert items_3[0].name == EXAMPLE_DATA["reverse_many_to_many_rels"][0]["name"]


def test_nesting_model_serializer__unique_error():
    ExampleFactory.create(name="foo", number=1)

    serializer = ExampleSerializer(data=EXAMPLE_DATA)
    assert serializer.is_valid(raise_exception=True)

    msg = "Example unique violation message."
    with pytest.raises(ValidationError, match=re.escape(msg)):
        serializer.save()


def test_nesting_model_serializer__constraint_error():
    data = deepcopy(EXAMPLE_DATA)
    data["name"] = "bar"
    serializer = ExampleSerializer(data=data)
    assert serializer.is_valid(raise_exception=True)

    msg = "Example constraint violation message."
    with pytest.raises(ValidationError, match=re.escape(msg)):
        serializer.save()


def test_serializer_get_or_default():
    serializer = ExampleSerializer(data=EXAMPLE_DATA)
    assert serializer.get_or_default("name", EXAMPLE_DATA) == "foo"
    assert serializer.get_or_default("state", EXAMPLE_DATA) == NOT_PROVIDED


@pytest.mark.django_db()
def test_serializer_request_user():
    request = Request(HttpRequest())
    request.user = user = User.objects.create_user(username="foo", email="foo@example.com")
    serializer = ExampleSerializer(context={"request": request})
    assert serializer.request_user == user
