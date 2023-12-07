import re

import pytest
from rest_framework.exceptions import NotFound

from graphene_django_extensions.model_operations import RelatedFieldInfo, get_object_or_404, get_related_field_info
from tests.example.models import Example
from tests.factories import ExampleFactory


def test_get_related_field_info():
    info = get_related_field_info(Example)
    assert info == {
        "reverse_one_to_one_rel": RelatedFieldInfo(name="example_field", forward=False, relation="one_to_one"),
        "reverse_one_to_many_rels": RelatedFieldInfo(name="example_field", forward=False, relation="one_to_many"),
        "reverse_many_to_many_rels": RelatedFieldInfo(name="example_fields", forward=False, relation="many_to_many"),
        "forward_one_to_one_field": RelatedFieldInfo(name="example_rel", forward=True, relation="one_to_one"),
        "forward_many_to_one_field": RelatedFieldInfo(name="example_rels", forward=True, relation="many_to_one"),
        "symmetrical_field": RelatedFieldInfo(name="symmetrical_field", forward=True, relation="many_to_many"),
        "forward_many_to_many_fields": RelatedFieldInfo(name="example_rels", forward=True, relation="many_to_many"),
    }


def test_related_field_info():
    info = RelatedFieldInfo(name="example_field", forward=True, relation="one_to_one")
    assert info.reverse is False
    assert info.one_to_one is True
    assert info.many_to_one is False
    assert info.one_to_many is False
    assert info.many_to_many is False

    info = RelatedFieldInfo(name="example_field", forward=True, relation="many_to_one")
    assert info.reverse is False
    assert info.one_to_one is False
    assert info.many_to_one is True
    assert info.one_to_many is False
    assert info.many_to_many is False

    info = RelatedFieldInfo(name="example_field", forward=False, relation="one_to_many")
    assert info.reverse is True
    assert info.one_to_one is False
    assert info.many_to_one is False
    assert info.one_to_many is True
    assert info.many_to_many is False

    info = RelatedFieldInfo(name="example_field", forward=False, relation="many_to_many")
    assert info.reverse is True
    assert info.one_to_one is False
    assert info.many_to_one is False
    assert info.one_to_many is False
    assert info.many_to_many is True


@pytest.mark.django_db()
def test_get_object_or_404():
    msg = "`Example` object matching query `{'pk': 1}` does not exist."
    with pytest.raises(NotFound, match=re.escape(msg)):
        get_object_or_404(Example, pk=1)

    example = ExampleFactory.create()
    assert get_object_or_404(Example, pk=example.pk) == example
