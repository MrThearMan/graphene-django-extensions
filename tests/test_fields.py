import datetime as dt
import re

import graphene
import pytest
from django import forms
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import models
from graphene.types.inputobjecttype import InputObjectTypeOptions
from graphql import GraphQLError, IntValueNode, StringValueNode, Undefined
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from example_project.app.models import Example, ExampleState, ForwardManyToOne
from graphene_django_extensions import ModelFilterSet
from graphene_django_extensions.converters import (
    convert_form_field_to_enum,
    convert_form_field_to_enum_list,
    convert_form_field_to_int,
    convert_form_field_to_list_of_int,
    convert_form_field_to_time,
    convert_time_to_string,
)
from graphene_django_extensions.fields import (
    Duration,
    DurationField,
    EnumChoiceField,
    EnumFriendlyChoiceField,
    EnumMultipleChoiceField,
    IntChoiceField,
    IntegerPrimaryKeyField,
    IntMultipleChoiceField,
    OrderingChoices,
    Time,
    UserDefinedFilterInputType,
)
from graphene_django_extensions.fields.graphql import Upload
from graphene_django_extensions.fields.model import IntChoiceField as IntChoiceModelField
from graphene_django_extensions.fields.model import StrChoiceField
from graphene_django_extensions.fields.serializer import IntPkOnlyObject
from graphene_django_extensions.filters import IntMultipleChoiceFilter
from tests.factories import ForwardManyToOneFactory


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


def test_filterset__no_fields():
    class MyFilterSet(ModelFilterSet):
        pk = IntMultipleChoiceFilter()

        class Meta:
            model = Example

    assert sorted(MyFilterSet.declared_filters) == ["order_by", "pk"]
    assert sorted(MyFilterSet._meta.fields) == []


def test_int_choice_field__valid_value__with_choices():
    field = IntChoiceField(choices=[(1, "one"), (2, "two")])
    assert field.valid_value(1) is True
    assert field.valid_value(3) is False


def test_int_choice_field__valid_value__without_choices():
    field = IntChoiceField()
    assert field.valid_value("1") is True
    assert field.valid_value("foo") is False
    assert field.valid_value(None) is False


def test_time_field_serialize__time():
    assert Time.serialize(dt.time(12, 30)) == "12:30:00"


def test_time_field_serialize__invalid_string():
    with pytest.raises(GraphQLError, match="Time cannot represent value"):
        Time.serialize("foo")


def test_duration_scalar__serialize():
    assert Duration.serialize(dt.timedelta(minutes=2)) == 120
    assert Duration.serialize(120) is None


def test_duration_scalar__parse_value():
    assert Duration.parse_value(120) == dt.timedelta(minutes=2)
    assert Duration.parse_value("120") is None


def test_duration_scalar__parse_literal():
    assert Duration.parse_literal(IntValueNode(value="120")) == 120
    assert Duration.parse_literal(StringValueNode(value="120")) is Undefined


def test_upload_scalar():
    file = SimpleUploadedFile("foo.txt", b"foo")
    assert Upload.serialize(file) is file
    assert Upload.parse_literal(file) is file
    assert Upload.parse_value(file) is file


def test_ordering_choices__model_required():
    with pytest.raises(TypeError, match=re.escape("'Meta.model' is required.")):
        type("FooOrderingChoices", (OrderingChoices,), {}, fields_map={"name": "name"})


def test_ordering_choices__fields_map_required():
    with pytest.raises(TypeError, match=re.escape("'Meta.fields' is required.")):
        type("FooOrderingChoices", (OrderingChoices,), {}, model=Example)


def test_user_defined_filter_input_type__model_required():
    with pytest.raises(TypeError, match=re.escape("'Meta.model' is required.")):
        type("FooFilterInput", (UserDefinedFilterInputType,), {}, fields_map={"name": "name"})


def test_user_defined_filter_input_type__fields_map_required():
    with pytest.raises(TypeError, match=re.escape("'Meta.fields' is required.")):
        type("FooFilterInput", (UserDefinedFilterInputType,), {}, model=Example)


def test_user_defined_filter_input_type__custom_options():
    options = InputObjectTypeOptions(UserDefinedFilterInputType)

    input_type = type(
        "FooFilterInput",
        (UserDefinedFilterInputType,),
        {},
        model=Example,
        fields_map={"name": "name"},
        _meta=options,
    )

    assert input_type._meta is options
    assert sorted(options.fields) == ["field", "operation", "operations", "value"]


@pytest.mark.django_db
def test_integer_primary_key_field__get_attribute():
    related = ForwardManyToOneFactory.create()
    field = IntegerPrimaryKeyField(queryset=ForwardManyToOne.objects.all())
    field.bind("forward_many_to_one_field", serializers.Serializer())

    value = field.get_attribute(Example(forward_many_to_one_field=related))

    assert isinstance(value, IntPkOnlyObject)
    assert int(value) == related.pk


def test_integer_primary_key_field__get_attribute__no_related_object():
    field = IntegerPrimaryKeyField(queryset=ForwardManyToOne.objects.all())
    field.bind("forward_many_to_one_field", serializers.Serializer())

    assert field.get_attribute(Example()) is None


def test_enum_friendly_choice_field__to_internal_value():
    field = EnumFriendlyChoiceField(choices=ExampleState.choices)
    assert field.to_internal_value("ACTIVE") == "ACTIVE"
    assert field.to_internal_value(ExampleState.ACTIVE) == "ACTIVE"


def test_enum_friendly_choice_field__to_internal_value__blank():
    field = EnumFriendlyChoiceField(choices=ExampleState.choices, allow_blank=True)
    assert field.to_internal_value("") == ""


def test_enum_friendly_choice_field__to_internal_value__invalid():
    field = EnumFriendlyChoiceField(choices=ExampleState.choices)
    with pytest.raises(ValidationError, match="is not a valid choice"):
        field.to_internal_value("foo")


def test_enum_friendly_choice_field__to_representation():
    field = EnumFriendlyChoiceField(choices=ExampleState.choices)
    assert field.to_representation("ACTIVE") == "ACTIVE"
    assert field.to_representation(ExampleState.INACTIVE) == "INACTIVE"
    assert field.to_representation("foo") == "foo"
    assert field.to_representation("") == ""
    assert field.to_representation(None) is None


def test_duration_field__to_internal_value():
    field = DurationField()
    assert field.to_internal_value(dt.timedelta(seconds=5)) == dt.timedelta(seconds=5)
    assert field.to_internal_value(5) == dt.timedelta(seconds=5)
    assert field.to_internal_value("5") == dt.timedelta(seconds=5)


def test_duration_field__to_internal_value__invalid():
    field = DurationField()
    with pytest.raises(ValidationError, match="A valid integer is required"):
        field.to_internal_value("foo")


def test_duration_field__to_representation():
    field = DurationField()
    assert field.to_representation(dt.timedelta(minutes=1)) == 60


def test_duration_field__get_attribute():
    field = DurationField()
    field.bind("duration", serializers.Serializer())
    assert field.get_attribute(Example(duration=dt.timedelta(minutes=1))) == 60
    assert field.get_attribute(Example(duration=None)) is None


def test_str_choice_field():
    field = StrChoiceField(enum=ExampleState)
    assert field.max_length == len("INACTIVE")
    assert field.choices == ExampleState.choices

    _name, _path, _args, kwargs = field.deconstruct()
    assert kwargs["enum"] is ExampleState


class Priority(models.IntegerChoices):
    LOW = 1
    HIGH = 3


def test_int_choice_model_field():
    field = IntChoiceModelField(enum=Priority)
    assert field.choices is None
    assert [(validator.limit_value, validator.message) for validator in field.validators] == [
        (1, "Value must be between 1 and 3."),
        (3, "Value must be between 1 and 3."),
    ]

    _name, _path, _args, kwargs = field.deconstruct()
    assert kwargs["enum"] is Priority


def test_int_choice_model_field__validate():
    field = IntChoiceModelField(enum=Priority)
    field.validate(3, None)

    with pytest.raises(DjangoValidationError, match=re.escape("Value 2 is not a valid choice.")):
        field.validate(2, None)

    # Choices are only used during validation.
    assert field.choices is None


def test_int_choice_model_field__formfield():
    field = IntChoiceModelField(enum=Priority)
    form_field = field.formfield()

    assert isinstance(form_field, forms.TypedChoiceField)
    # The label of the blank choice differs between Django versions.
    assert list(form_field.choices)[1:] == [(1, "Low"), (3, "High")]
    assert field.choices is None
