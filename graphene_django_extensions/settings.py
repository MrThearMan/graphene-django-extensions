from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.test.signals import setting_changed
from settings_holder import SettingsHolder, reload_settings

from .typing import Any, Literal, NamedTuple

if TYPE_CHECKING:
    from django.db import models

SETTING_NAME: str = "GRAPHENE_DJANGO_EXTENSIONS"


class DefaultSettings(NamedTuple):
    QUERY_PERMISSION_ERROR_MESSAGE: str = "No permission to access node."
    QUERY_PERMISSION_ERROR_CODE: str = "NODE_PERMISSION_DENIED"
    FILTER_PERMISSION_ERROR_MESSAGE: str = "No permission to access node."
    FILTER_PERMISSION_ERROR_CODE: str = "FILTER_PERMISSION_DENIED"
    FIELD_PERMISSION_ERROR_MESSAGE: str = "No permission to access field."
    FIELD_PERMISSION_ERROR_CODE: str = "FIELD_PERMISSION_DENIED"
    MUTATION_PERMISSION_ERROR_MESSAGE: str = "No permission to mutate."
    MUTATION_PERMISSION_ERROR_CODE: str = "MUTATION_PERMISSION_DENIED"
    CREATE_PERMISSION_ERROR_MESSAGE: str = "No permission to create."
    CREATE_PERMISSION_ERROR_CODE: str = "CREATE_PERMISSION_DENIED"
    UPDATE_PERMISSION_ERROR_MESSAGE: str = "No permission to update."
    UPDATE_PERMISSION_ERROR_CODE: str = "UPDATE_PERMISSION_DENIED"
    DELETE_PERMISSION_ERROR_MESSAGE: str = "No permission to delete."
    DELETE_PERMISSION_ERROR_CODE: str = "DELETE_PERMISSION_DENIED"
    MUTATION_VALIDATION_ERROR_MESSAGE: str = "Mutation was unsuccessful."
    MUTATION_VALIDATION_ERROR_CODE: str = "MUTATION_VALIDATION_ERROR"
    NOT_FOUND_ERROR_CODE: str = "NOT_FOUND"
    ORDERING_FILTER_NAME: str = "order_by"
    EXTEND_USER_DEFINED_FILTER_OPERATIONS: list[str] | None = None
    ALLOW_MODEL_OBJECT_TYPE_REGISTRY_OVERRIDES: bool = True
    EXPERIMENTAL_TRANSLATION_FIELDS: bool = False
    EXPERIMENTAL_TRANSLATION_FIELDS_KIND: Literal["list", "types"] = "list"


DEFAULTS: dict[str, Any] = DefaultSettings()._asdict()

IMPORT_STRINGS: set[bytes | str] = set()
REMOVED_SETTINGS: set[str] = {
    "PERMISSION_DENIED_MESSAGE",
}


def _validate_experimental_translation_fields_kind(value: Any) -> None:  # pragma: no cover
    if value not in ("list", "types"):
        msg = (
            f"Value `{value}` is not valid for `EXPERMENTAL_TRANSLATION_FIELDS_KIND`. "
            f"Valid values are `list` and `types`."
        )
        raise ValueError(msg)


gdx_settings = SettingsHolder(
    setting_name=SETTING_NAME,
    defaults=DEFAULTS,
    import_strings=IMPORT_STRINGS,
    removed_settings=REMOVED_SETTINGS,
    validators={
        "EXPERMENTAL_TRANSLATION_FIELDS_KIND": _validate_experimental_translation_fields_kind,
    },
)

reload_my_settings = reload_settings(SETTING_NAME, gdx_settings)
setting_changed.connect(reload_my_settings)


# Override the default Enum name generator to have PascalCase names everywhere


def enum_name(field: models.Field) -> str:
    # If using `StrChoiceField` or `IntChoiceField`, use the stored enum name.
    if hasattr(field, "enum") and field.enum is not None:  # pragma: no cover
        return field.enum.__name__
    # Otherwise, generate the name from the field name.
    return "".join(s.capitalize() for s in field.name.split("_"))


if not hasattr(settings, "GRAPHENE"):  # pragma: no cover
    settings.GRAPHENE = {}

settings.GRAPHENE.setdefault("DJANGO_CHOICE_FIELD_ENUM_CUSTOM_NAME", "graphene_django_extensions.settings.enum_name")
