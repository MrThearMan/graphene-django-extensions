from django.test.signals import setting_changed
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
