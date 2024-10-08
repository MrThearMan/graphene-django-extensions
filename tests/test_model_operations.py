import re

import pytest

from example_project.app.models import Example
from graphene_django_extensions.errors import GQLNotFoundError
from graphene_django_extensions.model_operations import RelatedFieldInfo, get_object_or_404, get_related_field_info
from tests.factories import ExampleFactory


def test_get_related_field_info():
    info = get_related_field_info(Example)
    assert info == {
        "reverse_one_to_one_rel": RelatedFieldInfo(
            field_name="reverse_one_to_one_rel",
            related_name="example_field",
            forward=False,
            relation="one_to_one",
        ),
        "reverse_one_to_many_rels": RelatedFieldInfo(
            field_name="reverse_one_to_many_rels",
            related_name="example_field",
            forward=False,
            relation="one_to_many",
        ),
        "reverse_many_to_many_rels": RelatedFieldInfo(
            field_name="reverse_many_to_many_rels",
            related_name="example_fields",
            forward=False,
            relation="many_to_many",
        ),
        "forward_one_to_one_field": RelatedFieldInfo(
            field_name="forward_one_to_one_field",
            related_name="example_rel",
            forward=True,
            relation="one_to_one",
        ),
        "forward_many_to_one_field": RelatedFieldInfo(
            field_name="forward_many_to_one_field",
            related_name="example_rels",
            forward=True,
            relation="many_to_one",
        ),
        "symmetrical_field": RelatedFieldInfo(
            field_name="symmetrical_field",
            related_name="symmetrical_field",
            forward=True,
            relation="many_to_many",
        ),
        "forward_many_to_many_fields": RelatedFieldInfo(
            field_name="forward_many_to_many_fields",
            related_name="example_rels",
            forward=True,
            relation="many_to_many",
        ),
    }


def test_related_field_info():
    info = RelatedFieldInfo(
        field_name="forward_one_to_one_field",
        related_name="example_field",
        forward=True,
        relation="one_to_one",
    )
    assert info.reverse is False
    assert info.one_to_one is True
    assert info.many_to_one is False
    assert info.one_to_many is False
    assert info.many_to_many is False

    info = RelatedFieldInfo(
        field_name="forward_many_to_one_field",
        related_name="example_field",
        forward=True,
        relation="many_to_one",
    )
    assert info.reverse is False
    assert info.one_to_one is False
    assert info.many_to_one is True
    assert info.one_to_many is False
    assert info.many_to_many is False

    info = RelatedFieldInfo(
        field_name="reverse_one_to_many_rels",
        related_name="example_field",
        forward=False,
        relation="one_to_many",
    )
    assert info.reverse is True
    assert info.one_to_one is False
    assert info.many_to_one is False
    assert info.one_to_many is True
    assert info.many_to_many is False

    info = RelatedFieldInfo(
        field_name="reverse_many_to_many_rels",
        related_name="example_field",
        forward=False,
        relation="many_to_many",
    )
    assert info.reverse is True
    assert info.one_to_one is False
    assert info.many_to_one is False
    assert info.one_to_many is False
    assert info.many_to_many is True


@pytest.mark.django_db()
def test_get_object_or_404():
    msg = "`Example` object matching query `{'pk': 1}` does not exist."
    with pytest.raises(GQLNotFoundError, match=re.escape(msg)):
        get_object_or_404(Example, pk=1)

    example = ExampleFactory.create()
    assert get_object_or_404(Example, pk=example.pk) == example
