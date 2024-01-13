import graphene
from django import forms
from django.db import models

from graphene_django_extensions.fields import (
    EnumChoiceField,
    EnumMultipleChoiceField,
    IntChoiceField,
    IntMultipleChoiceField,
    Time,
    convert_form_field_to_enum,
    convert_form_field_to_enum_list,
    convert_form_field_to_int,
    convert_form_field_to_list_of_int,
    convert_form_field_to_time,
    convert_time_to_string,
)
from tests.example.models import ExampleState


def test_time_field_serialize():
    obj = Time()
    assert obj.serialize("12:00:00") == "12:00:00"


def test_convert_time_to_string():
    obj = convert_time_to_string(field=models.TimeField(help_text="test help text"))
    assert type(obj) is Time
    assert obj.kwargs["description"] == "test help text"
    assert obj.kwargs["required"] is True


def test_convert_form_field_to_time():
    obj = convert_form_field_to_time(field=forms.TimeField(help_text="test help text"))
    assert type(obj) is Time
    assert obj.kwargs["description"] == "test help text"
    assert obj.kwargs["required"] is True


def test_convert_form_field_to_int():
    obj = convert_form_field_to_int(field=IntChoiceField(help_text="test help text"))
    assert type(obj) is graphene.Int
    assert obj.kwargs["description"] == "test help text"
    assert obj.kwargs["required"] is True


def test_convert_form_field_to_list_of_int():
    obj = convert_form_field_to_list_of_int(field=IntMultipleChoiceField(help_text="test help text"))
    assert type(obj) is graphene.List
    assert obj.of_type is graphene.Int
    assert obj.kwargs["description"] == "test help text"
    assert obj.kwargs["required"] is True


def test_convert_form_field_to_enum():
    obj = convert_form_field_to_enum(field=EnumChoiceField(enum=ExampleState, help_text="test help text"))
    assert issubclass(type(obj), graphene.Enum)
    assert obj.kwargs["description"] == "test help text"
    assert obj.kwargs["required"] is True


def test_convert_form_field_to_enum_list():
    obj = convert_form_field_to_enum_list(field=EnumMultipleChoiceField(enum=ExampleState, help_text="test help text"))
    assert type(obj) is graphene.List
    assert issubclass(obj.of_type, graphene.Enum)
    assert obj.kwargs["description"] == "test help text"
    assert obj.kwargs["required"] is True
