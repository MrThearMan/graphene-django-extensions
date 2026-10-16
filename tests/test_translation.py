from __future__ import annotations

import sys

import pytest

from example_project.app.models import Example, ForwardOneToOne
from graphene_django_extensions.translation import (
    LanguageListField,
    TranslationsField,
    add_translatable_fields,
    get_available_languages,
    get_translatable_fields,
)


@pytest.fixture
def no_modeltranslation(monkeypatch):
    # A `None` entry in `sys.modules` makes the import raise an `ImportError`.
    monkeypatch.setitem(sys.modules, "modeltranslation.manager", None)
    monkeypatch.setitem(sys.modules, "modeltranslation.settings", None)
    monkeypatch.setitem(sys.modules, "modeltranslation.utils", None)
    get_available_languages.cache_clear()
    yield
    get_available_languages.cache_clear()


def test_get_translatable_fields():
    assert get_translatable_fields(Example) == ["name"]


def test_get_translatable_fields__model_not_translated():
    assert get_translatable_fields(ForwardOneToOne) == []


def test_get_translatable_fields__modeltranslation_not_installed(no_modeltranslation):
    assert get_translatable_fields(Example) == []


def test_add_translatable_fields():
    fields = add_translatable_fields(Example, ["pk", "name"])
    assert fields == ["pk", "name", "name_en", "name_fi"]


def test_add_translatable_fields__remove_base_fields():
    fields = add_translatable_fields(Example, ["pk", "name"], remove_base_fields=True)
    assert fields == ["pk", "name_en", "name_fi"]


def test_add_translatable_fields__modeltranslation_not_installed(no_modeltranslation):
    fields = ["pk", "name"]
    assert add_translatable_fields(Example, fields) is fields


def test_get_available_languages():
    assert get_available_languages() == ["en", "fi"]


def test_get_available_languages__modeltranslation_not_installed(no_modeltranslation):
    assert get_available_languages() == []


@pytest.mark.parametrize("field_class", [TranslationsField, LanguageListField])
def test_translation_field__custom_resolver_is_kept(field_class):
    def resolver(root, info):
        return None

    field = field_class(field_name="name")
    assert field.wrap_resolve(resolver) is resolver
