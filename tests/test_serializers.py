import re
from copy import deepcopy
from typing import Any

import pytest
from rest_framework.exceptions import ValidationError

from graphene_django_extensions.serializers import BaseModelSerializer
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


class ForwardOneToOneSerializer(BaseModelSerializer):
    class Meta:
        model = ForwardOneToOne
        fields = [
            "pk",
            "name",
        ]


class ForwardManyToManySerializer(BaseModelSerializer):
    class Meta:
        model = ForwardManyToMany
        fields = [
            "pk",
            "name",
        ]


class ForwardManyToOneSerializer(BaseModelSerializer):
    class Meta:
        model = ForwardManyToOne
        fields = [
            "pk",
            "name",
        ]


class ReverseOneToOneSerializer(BaseModelSerializer):
    class Meta:
        model = ReverseOneToOne
        fields = [
            "pk",
            "name",
        ]


class ReverseManyToManySerializer(BaseModelSerializer):
    class Meta:
        model = ReverseManyToMany
        fields = [
            "pk",
            "name",
        ]


class ReverseOneToManySerializer(BaseModelSerializer):
    class Meta:
        model = ReverseOneToMany
        fields = [
            "pk",
            "name",
        ]


class ExampleSerializer(BaseModelSerializer):
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


def test_base_model_serializer__create():
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


def test_base_model_serializer__create__unique_error():
    ExampleFactory.create(name="foo", number=1)

    serializer = ExampleSerializer(data=EXAMPLE_DATA)
    assert serializer.is_valid(raise_exception=True)

    msg = "Example unique violation message."
    with pytest.raises(ValidationError, match=re.escape(msg)):
        serializer.save()


def test_base_model_serializer__create__constraint_error():
    data = deepcopy(EXAMPLE_DATA)
    data["name"] = "bar"
    serializer = ExampleSerializer(data=data)
    assert serializer.is_valid(raise_exception=True)

    msg = "Example constraint violation message."
    with pytest.raises(ValidationError, match=re.escape(msg)):
        serializer.save()
