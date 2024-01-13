from django.conf import settings
from django.db import models
from django.test.signals import setting_changed
from graphene.types.enum import Enum
from graphene_django.converter import convert_choices_to_named_enum_with_descriptions
from graphene_django.rest_framework.serializer_converter import get_graphene_type_from_serializer_field
from rest_framework import serializers
from settings_holder import SettingsHolder, reload_settings

from .typing import Any, NamedTuple, Union

SETTING_NAME: str = "GRAPHENE_DJANGO_EXTENSIONS"


class DefaultSettings(NamedTuple):
    QUERY_PERMISSION_ERROR_MESSAGE: str = "No permission to access node."
    FILTER_PERMISSION_ERROR_MESSAGE: str = "No permission to access node."
    FIELD_PERMISSION_ERROR_MESSAGE: str = "No permission to access field."
    MUTATION_PERMISSION_ERROR_MESSAGE: str = "No permission to mutate."
    CREATE_PERMISSION_ERROR_MESSAGE: str = "No permission to create."
    UPDATE_PERMISSION_ERROR_MESSAGE: str = "No permission to update."
    DELETE_PERMISSION_ERROR_MESSAGE: str = "No permission to delete."
    ORDERING_FILTER_NAME: str = "order_by"


DEFAULTS: dict[str, Any] = DefaultSettings()._asdict()

IMPORT_STRINGS: set[Union[bytes, str]] = set()
REMOVED_SETTINGS: set[str] = {
    "PERMISSION_DENIED_MESSAGE",
}

gdx_settings = SettingsHolder(
    setting_name=SETTING_NAME,
    defaults=DEFAULTS,
    import_strings=IMPORT_STRINGS,
    removed_settings=REMOVED_SETTINGS,
)

reload_my_settings = reload_settings(SETTING_NAME, gdx_settings)
setting_changed.connect(reload_my_settings)


# Override the default Enum name generator to have PascalCase names everywhere


def enum_name(field: models.Field) -> str:
    return "".join(s.capitalize() for s in field.name.split("_"))


if not hasattr(settings, "GRAPHENE"):  # pragma: no cover
    settings.GRAPHENE = {}

settings.GRAPHENE.setdefault("DJANGO_CHOICE_FIELD_ENUM_CUSTOM_NAME", "graphene_django_extensions.settings.enum_name")


@get_graphene_type_from_serializer_field.register
def convert_serializer_field_to_enum(field: serializers.ChoiceField) -> Enum:
    name = field.field_name or field.source or "Choices"
    name = "".join(s.capitalize() for s in name.split("_"))
    return convert_choices_to_named_enum_with_descriptions(name, field.choices)
