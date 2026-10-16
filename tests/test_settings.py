import re
from pathlib import Path

import pytest
from django.conf import settings as django_settings
from django.test.signals import setting_changed

from example_project.app.models import Example, ExampleState
from graphene_django_extensions import settings as gdx_settings_module
from graphene_django_extensions.fields.model import StrChoiceField
from graphene_django_extensions.settings import _validate_experimental_translation_fields_kind, enum_name


@pytest.mark.parametrize("value", ["list", "types"])
def test_validate_experimental_translation_fields_kind(value):
    _validate_experimental_translation_fields_kind(value)


def test_validate_experimental_translation_fields_kind__invalid():
    msg = "Value `foo` is not valid for `EXPERIMENTAL_TRANSLATION_FIELDS_KIND`. Valid values are `list` and `types`."
    with pytest.raises(ValueError, match=re.escape(msg)):
        _validate_experimental_translation_fields_kind("foo")


def test_experimental_translation_fields_kind__invalid_setting(settings):
    settings.GRAPHENE_DJANGO_EXTENSIONS = {**settings.GRAPHENE_DJANGO_EXTENSIONS, "EXPERIMENTAL_TRANSLATION_FIELDS_KIND": "foo"}

    msg = "Value `foo` is not valid for `EXPERIMENTAL_TRANSLATION_FIELDS_KIND`. Valid values are `list` and `types`."
    with pytest.raises(ValueError, match=re.escape(msg)):
        gdx_settings_module.gdx_settings.EXPERIMENTAL_TRANSLATION_FIELDS_KIND  # noqa: B018


def test_enum_name__from_field_name():
    assert enum_name(Example._meta.get_field("example_state")) == "ExampleState"


def test_enum_name__from_enum():
    field = StrChoiceField(enum=ExampleState)
    field.name = "state"
    assert enum_name(field) == "ExampleState"


def test_enum_name_set_for_graphene():
    assert django_settings.GRAPHENE["DJANGO_CHOICE_FIELD_ENUM_CUSTOM_NAME"] == (
        "graphene_django_extensions.settings.enum_name"
    )


def test_enum_name_set_for_graphene__no_graphene_settings(settings):
    del settings.GRAPHENE

    # Run the settings module again in a separate namespace to see how it sets up the "GRAPHENE" setting.
    path = Path(gdx_settings_module.__file__)
    namespace = {"__name__": "gdx_settings_copy", "__package__": "graphene_django_extensions"}
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), namespace)  # noqa: S102
    setting_changed.disconnect(namespace["reload_my_settings"])

    assert settings.GRAPHENE == {
        "DJANGO_CHOICE_FIELD_ENUM_CUSTOM_NAME": "graphene_django_extensions.settings.enum_name",
    }
