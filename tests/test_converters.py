import re
from typing import TypedDict

import graphene
import pytest

from graphene_django_extensions.fields import TypedDictField


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
