from __future__ import annotations

import datetime as dt
import re
from copy import deepcopy
from typing import Any

import pytest
from django.contrib.auth.models import User
from django.http import HttpRequest
from rest_framework import __version__ as drf_version
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request

from example_project.app.models import (
    Example,
    ExampleState,
    ForwardManyToMany,
    ForwardManyToOne,
    ForwardOneToOne,
    ReverseManyToMany,
    ReverseOneToMany,
    ReverseOneToOne,
)
from graphene_django_extensions.converters import convert_serializer_fields_to_not_required
from graphene_django_extensions.serializers import NestingModelSerializer, NotProvided
from tests.factories import (
    ExampleFactory,
    ForwardManyToManyFactory,
    ForwardManyToOneFactory,
    ForwardOneToOneFactory,
    ReverseManyToManyFactory,
    ReverseOneToManyFactory,
    ReverseOneToOneFactory,
)

DRF_VERSION = tuple(int(i) for i in drf_version.split("."))


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
            "duration",
            "example_state",
            "forward_one_to_one_field",
            "forward_many_to_one_field",
            "forward_many_to_many_fields",
            "reverse_one_to_one_rel",
            "reverse_one_to_many_rels",
            "reverse_many_to_many_rels",
        ]


def get_example_data() -> dict[str, Any]:
    return {
        "name": "foo",
        "name_fi": "foo",
        "name_en": "foo",
        "number": 1,
        "email": "foofoo@email.com",
        "duration": int(dt.timedelta(seconds=900).total_seconds()),
        "example_state": ExampleState.ACTIVE.value,
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


class ExampleSerializerNoFields(NestingModelSerializer):
    class Meta:
        model = Example
        fields = [
            "pk",
            "name",
            "number",
            "email",
            "duration",
            "example_state",
            "forward_one_to_one_field",
            "forward_many_to_one_field",
            "forward_many_to_many_fields",
            "reverse_one_to_one_rel",
            "reverse_one_to_many_rels",
            "reverse_many_to_many_rels",
        ]


def get_example_data_no_fields() -> dict[str, Any]:
    f_o2o = ForwardOneToOneFactory.create(name="one")
    f_m2o = ForwardManyToOneFactory.create(name="two")
    f_m2m = ForwardManyToManyFactory.create(name="three")
    r_oto = ReverseOneToOneFactory.create(name="four")
    r_otm = ReverseOneToManyFactory.create(name="five")
    r_m2m = ReverseManyToManyFactory.create(name="six")

    return {
        "name": "foo",
        "name_fi": "foo",
        "name_en": "foo",
        "number": 1,
        "email": "foofoo@email.com",
        "duration": int(dt.timedelta(seconds=900).total_seconds()),
        "example_state": ExampleState.ACTIVE.value,
        "forward_one_to_one_field": f_o2o.pk,
        "forward_many_to_one_field": f_m2o.pk,
        "forward_many_to_many_fields": [f_m2m.pk],
        "reverse_one_to_one_rel": r_oto.pk,
        "reverse_one_to_many_rels": [r_otm.pk],
        "reverse_many_to_many_rels": [r_m2m.pk],
    }


def test_nesting_model_serializer__create():
    serializer = ExampleSerializer(data=get_example_data())
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

    update_data = deepcopy(get_example_data())
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

    example_data = get_example_data()
    assert examples[0].name == example_data["name"]

    # Forward relations
    assert examples[0].forward_one_to_one_field.pk == oto_pk
    assert examples[0].forward_one_to_one_field.name == example_data["forward_one_to_one_field"]["name"]
    assert examples[0].forward_many_to_one_field.pk == mto_pk
    assert examples[0].forward_many_to_one_field.name == mto_name
    assert items_1[0].name == example_data["forward_many_to_many_fields"][0]["name"]

    # Reverse relations
    assert examples[0].reverse_one_to_one_rel.name == example_data["reverse_one_to_one_rel"]["name"]
    assert items_2[0].name == example_data["reverse_one_to_many_rels"][0]["name"]
    assert items_3[0].name == example_data["reverse_many_to_many_rels"][0]["name"]


@pytest.mark.skipif(DRF_VERSION >= (3, 15), reason="Unique errors are raised during validation after DRF 3.15.")
def test_nesting_model_serializer__unique_error():
    ExampleFactory.create(name="foo", number=1)

    serializer = ExampleSerializer(data=get_example_data())
    assert serializer.is_valid(raise_exception=True)

    msg = "Example unique violation message."
    with pytest.raises(ValidationError, match=re.escape(msg)):
        serializer.save()


def test_nesting_model_serializer__constraint_error():
    data = get_example_data()
    data["name"] = "bar"
    data["name_fi"] = "bar"
    data["name_en"] = "bar"
    serializer = ExampleSerializer(data=data)
    assert serializer.is_valid(raise_exception=True)

    msg = "Example constraint violation message."
    with pytest.raises(ValidationError, match=re.escape(msg)):
        serializer.save()


def test_serializer_get_or_default():
    data = get_example_data()
    data.pop("example_state", None)
    serializer = ExampleSerializer(data=data)
    assert serializer.get_or_default("name", data) == "foo"
    assert serializer.get_or_default("example_state", data) == NotProvided


@pytest.mark.django_db
def test_serializer_request_user():
    request = Request(HttpRequest())
    request.user = user = User.objects.create_user(username="foo", email="foo@example.com")
    serializer = ExampleSerializer(context={"request": request})
    assert serializer.request_user == user


def test_nesting_model_serializer__integer_fields():
    serializer = ExampleSerializerNoFields(data=get_example_data_no_fields())
    assert serializer.is_valid(raise_exception=True)
    serializer.save()

    example = Example.objects.filter(name="foo").first()
    f_m2m = example.forward_many_to_many_fields.first()
    r_o2m = example.reverse_one_to_many_rels.first()
    r_m2m = example.reverse_many_to_many_rels.first()

    # Forward relations
    assert example.forward_one_to_one_field.name == "one"
    assert example.forward_many_to_one_field.name == "two"
    assert f_m2m.name == "three"

    # Reverse relations
    assert example.reverse_one_to_one_rel.name == "four"
    assert r_o2m.name == "five"
    assert r_m2m.name == "six"


def test_not_provided_is_falsy():
    assert not NotProvided


def test_nesting_model_serializer__all_fields():
    class ForwardOneToOneAllFieldsSerializer(NestingModelSerializer):
        class Meta:
            model = ForwardOneToOne
            fields = "__all__"

    serializer = ForwardOneToOneAllFieldsSerializer()

    assert ForwardOneToOneAllFieldsSerializer.Meta.fields == "__all__"
    assert "name" in serializer.fields


def test_nesting_model_serializer__create__validated_data_missing():
    serializer = ExampleSerializer()

    with pytest.raises(ValueError, match=re.escape("'validated_data' not found in args or kwargs")):
        serializer.create(validated_data=None)


def test_nesting_model_serializer__get_update_or_create__no_data():
    serializer = ForwardOneToOneSerializer()

    assert serializer.get_update_or_create(None) is None


class ExampleNullableRelationsSerializer(NestingModelSerializer):
    forward_many_to_many_fields = ForwardManyToManySerializer(many=True, allow_null=True, required=False)
    reverse_one_to_one_rel = ReverseOneToOneSerializer(allow_null=True, required=False)
    reverse_one_to_many_rels = ReverseOneToManySerializer(many=True, allow_null=True, required=False)

    class Meta:
        model = Example
        fields = [
            "pk",
            "name",
            "forward_many_to_many_fields",
            "reverse_one_to_one_rel",
            "reverse_one_to_many_rels",
        ]


def test_nesting_model_serializer__many_to_many__null():
    example = ExampleFactory.create(forward_many_to_many_fields=[ForwardManyToManyFactory.create()])

    data = {"forward_many_to_many_fields": None}
    serializer = ExampleNullableRelationsSerializer(instance=example, data=data, partial=True)
    assert serializer.is_valid(raise_exception=True)
    serializer.save()

    # Null means that the relations are not updated.
    assert example.forward_many_to_many_fields.count() == 1


def test_nesting_model_serializer__many_to_many__null_items_are_skipped():
    example = ExampleFactory.create()

    data = {"forward_many_to_many_fields": [None, {"name": "foo"}]}
    serializer = ExampleNullableRelationsSerializer(instance=example, data=data, partial=True)
    assert serializer.is_valid(raise_exception=True)
    serializer.save()

    items = list(example.forward_many_to_many_fields.all())
    assert len(items) == 1
    assert items[0].name == "foo"


def test_nesting_model_serializer__one_to_many__null_items_are_skipped():
    example = ExampleFactory.create()
    ReverseOneToManyFactory.create(example_field=example, name="old")

    data = {"reverse_one_to_many_rels": [None, {"name": "foo"}]}
    serializer = ExampleNullableRelationsSerializer(instance=example, data=data, partial=True)
    assert serializer.is_valid(raise_exception=True)
    serializer.save()

    # Items that were not given are deleted.
    items = list(example.reverse_one_to_many_rels.all())
    assert len(items) == 1
    assert items[0].name == "foo"


def test_nesting_model_serializer__reverse_one_to_one__null__no_related_object():
    example = ExampleFactory.create()

    data = {"reverse_one_to_one_rel": None}
    serializer = ExampleNullableRelationsSerializer(instance=example, data=data, partial=True)
    assert serializer.is_valid(raise_exception=True)
    serializer.save()

    assert not ReverseOneToOne.objects.exists()


def test_nesting_model_serializer__reverse_one_to_one__null__related_object_not_nullable():
    example = ExampleFactory.create()
    ReverseOneToOneFactory.create(example_field=example)

    data = {"reverse_one_to_one_rel": None}
    serializer = ExampleNullableRelationsSerializer(instance=example, data=data, partial=True)
    assert serializer.is_valid(raise_exception=True)

    # Unlinking the related object fails, since its relation to the example is not nullable.
    msg = "NOT NULL constraint failed: app_reverseonetoone.example_field_id"
    with pytest.raises(ValidationError, match=re.escape(msg)):
        serializer.save()

    assert ReverseOneToOne.objects.filter(example_field=example).exists()


class ReverseOneToOnePlainSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReverseOneToOne
        fields = ["pk", "name"]


class ReverseOneToManyPlainSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReverseOneToMany
        fields = ["pk", "name"]


class ReverseManyToManyPlainSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReverseManyToMany
        fields = ["pk", "name"]


class ExamplePlainNestedSerializer(NestingModelSerializer):
    reverse_one_to_one_rel = ReverseOneToOnePlainSerializer(required=False)
    reverse_one_to_many_rels = ReverseOneToManyPlainSerializer(many=True, required=False)
    reverse_many_to_many_rels = ReverseManyToManyPlainSerializer(many=True, required=False)

    class Meta:
        model = Example
        fields = [
            "pk",
            "name",
            "reverse_one_to_one_rel",
            "reverse_one_to_many_rels",
            "reverse_many_to_many_rels",
        ]


@pytest.mark.parametrize(
    ("field", "value", "model"),
    [
        ("reverse_one_to_one_rel", {"name": "foo"}, ReverseOneToOne),
        ("reverse_one_to_many_rels", [{"name": "foo"}], ReverseOneToMany),
        ("reverse_many_to_many_rels", [{"name": "foo"}], ReverseManyToMany),
    ],
)
def test_nesting_model_serializer__reverse_relation__plain_model_serializer_is_ignored(field, value, model):
    # Only nested 'NestingModelSerializers' and related fields are saved for reverse relations.
    example = ExampleFactory.create()

    serializer = ExamplePlainNestedSerializer(instance=example, data={field: value}, partial=True)
    assert serializer.is_valid(raise_exception=True)
    serializer.save()

    assert not model.objects.exists()
