import re
from typing import TypedDict
from unittest.mock import Mock

import graphene
import pytest
from django.contrib.sessions.models import Session
from django.db import models
from graphene_django.rest_framework.serializer_converter import get_graphene_type_from_serializer_field
from rest_framework import serializers

from example_project.app.models import Example, ExampleState
from graphene_django_extensions.converters import convert_serializer_fields_to_not_required, convert_to_one_related
from graphene_django_extensions.fields import Duration, DurationField, EnumFriendlyChoiceField, TypedDictField


def test_convert_typed_dict_to_graphene_type():
    class TestTypedDict(TypedDict):
        name: str
        age: int

    graphene_type = TypedDictField(TestTypedDict).type

    assert hasattr(graphene_type, "name") is True
    assert type(graphene_type.name) is graphene.String

    assert hasattr(graphene_type, "age") is True
    assert type(graphene_type.age) is graphene.Int


def test_convert_typed_dict_to_graphene_type__not_found():
    class TestTypedDict(TypedDict):
        example: None

    msg = "Cannot convert field `example` of type `NoneType` to model field."
    with pytest.raises(ValueError, match=re.escape(msg)):
        TypedDictField(TestTypedDict)


def test_convert_serializer_fields_to_not_required__declared_regular_field():
    class ExampleSerializer(serializers.ModelSerializer):
        email = serializers.EmailField(required=True)

        class Meta:
            model = Example
            fields = ["pk", "name", "email"]

    new_class = convert_serializer_fields_to_not_required(ExampleSerializer, None)

    # Regular declared fields are kept as is, only nested serializers are replaced.
    assert new_class._declared_fields["email"] is ExampleSerializer._declared_fields["email"]
    assert new_class.Meta.extra_kwargs["name"] == {"required": False}
    assert new_class.Meta.extra_kwargs["pk"] == {"required": True, "read_only": False}


def test_convert_serializer_field_to_enum__enum_name():
    field = EnumFriendlyChoiceField(choices=ExampleState.choices, enum=ExampleState)

    enum = get_graphene_type_from_serializer_field(field)

    assert enum._meta.name == "ExampleState"


def test_convert_serializer_field_to_enum__field_name():
    field = serializers.ChoiceField(choices=ExampleState.choices)
    field.bind("example_state", serializers.Serializer())

    enum = get_graphene_type_from_serializer_field(field)

    assert enum._meta.name == "ExampleState"


def test_convert_serializer_field_to_duration():
    assert get_graphene_type_from_serializer_field(DurationField()) is Duration


def test_convert_to_one_related__integer_primary_key():
    field = serializers.PrimaryKeyRelatedField(queryset=Example.objects.all())
    assert get_graphene_type_from_serializer_field(field) is graphene.Int


def test_convert_to_one_related__read_only():
    field = serializers.PrimaryKeyRelatedField(read_only=True)
    assert get_graphene_type_from_serializer_field(field) is graphene.ID


def test_convert_to_one_related__char_primary_key():
    field = serializers.PrimaryKeyRelatedField(queryset=Session.objects.all())
    assert get_graphene_type_from_serializer_field(field) is graphene.String


@pytest.mark.parametrize(
    ("primary_key_field", "expected"),
    [
        (models.UUIDField(primary_key=True), graphene.UUID),
        (models.DateField(primary_key=True), graphene.ID),
    ],
)
def test_convert_to_one_related__other_primary_keys(primary_key_field, expected):
    field = serializers.PrimaryKeyRelatedField(queryset=Example.objects.all())
    queryset = Mock()
    queryset.model._meta.pk = primary_key_field
    field.queryset = queryset

    assert convert_to_one_related(field) is expected


def test_convert_to_many_related():
    field = serializers.PrimaryKeyRelatedField(queryset=Example.objects.all(), many=True)
    assert get_graphene_type_from_serializer_field(field) == (graphene.List, graphene.Int)
