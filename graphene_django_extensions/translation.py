from __future__ import annotations

from functools import cache, partial
from typing import TYPE_CHECKING, Callable

import graphene
from graphene.types.objecttype import ObjectTypeOptions

if TYPE_CHECKING:
    from django.db import models

    from graphene_django_extensions.typing import Any, GQLInfo, Sequence

__all__ = [
    "LanguageListField",
    "LanguageString",
    "Translatable",
    "TranslationsField",
    "add_translatable_fields",
    "get_available_languages",
    "get_translatable_fields",
]


def get_translatable_fields(model: type[models.Model]) -> list[str]:
    """If `django-modeltranslation` is installed, find all translatable fields in the given model."""
    try:
        from modeltranslation.manager import get_translatable_fields_for_model
    except ImportError:
        return []

    return get_translatable_fields_for_model(model) or []


def add_translatable_fields(model: type[models.Model], fields: Sequence[str]) -> Sequence[str]:
    """
    If `django-modeltranslation` is installed, find and add all translation fields
    to the given fields list, for the given fields, in the given model.
    """
    try:
        from modeltranslation.manager import get_translatable_fields_for_model
        from modeltranslation.utils import get_translation_fields
    except ImportError:
        return fields

    translatable_fields: list[str] = get_translatable_fields_for_model(model) or []
    new_fields: list[str] = []
    for field in fields:
        new_fields.append(field)
        if field not in translatable_fields:
            continue
        fields = get_translation_fields(field)
        new_fields.extend(fields)

    return new_fields


@cache
def get_available_languages() -> list[str]:
    """Get a list of all available translation languages."""
    try:
        from modeltranslation.settings import AVAILABLE_LANGUAGES
    except ImportError:
        return []

    return AVAILABLE_LANGUAGES


class BaseTranslatable(graphene.ObjectType):
    @classmethod
    def __init_subclass_with_meta__(cls, **options: Any) -> None:
        # This method is run only on subclasses, which is why we need this base class.
        _meta = ObjectTypeOptions(cls)
        _meta.fields = {
            lang: graphene.Field(
                graphene.String,
                description=f"Translation in {lang}.",
            )
            for lang in get_available_languages()
        }
        super().__init_subclass_with_meta__(_meta=_meta, **options)


class Translatable(BaseTranslatable): ...


class LanguageString(graphene.ObjectType):
    language = graphene.String(required=True, description="Language code.")
    value = graphene.String(required=False, description="Translation in the given language.")


class TranslationsField(graphene.Field):
    def __init__(self, field_name: str, **kwargs: Any) -> None:
        kwargs["type_"] = graphene.NonNull(Translatable)
        self.field_name = field_name
        self.languages = get_available_languages()
        super().__init__(**kwargs)

    def wrap_resolve(self, parent_resolver: Callable) -> Callable:
        if isinstance(parent_resolver, partial):  # shorthand for default resolver
            return self.field_resolver
        return parent_resolver  # pragma: no cover

    def field_resolver(self, root: models.Model, info: GQLInfo) -> dict[str, str]:
        return {lang: getattr(root, f"{self.field_name}_{lang}") for lang in self.languages}


class LanguageListField(graphene.Field):
    def __init__(self, field_name: str, **kwargs: Any) -> None:
        kwargs["type_"] = graphene.List(graphene.NonNull(LanguageString))
        self.field_name = field_name
        self.languages = get_available_languages()
        super().__init__(**kwargs)

    def wrap_resolve(self, parent_resolver: Callable) -> Callable:
        if isinstance(parent_resolver, partial):  # shorthand for default resolver
            return self.field_resolver
        return parent_resolver  # pragma: no cover

    def field_resolver(self, root: models.Model, info: GQLInfo) -> list[dict[str, str]]:
        return [{"language": lang, "value": getattr(root, f"{self.field_name}_{lang}")} for lang in self.languages]
