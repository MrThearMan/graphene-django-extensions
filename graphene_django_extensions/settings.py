from django.test.signals import setting_changed
from settings_holder import SettingsHolder, reload_settings

from .typing import Any, NamedTuple, Union

SETTING_NAME: str = "GRAPHENE_DJANGO_EXTENSIONS"


class DefaultSettings(NamedTuple):
    QUERY_PERMISSION_ERROR_MESSAGE: str = "No permission to access node."
    FILTER_PERMISSION_ERROR_MESSAGE: str = "No permission to access node."
    MUTATION_PERMISSION_ERROR_MESSAGE: str = "No permission to mutate."
    ORDERING_FILTER_NAME: str = "order_by"
    PERMISSION_DENIED_MESSAGE: str = "You do not have permission to access this field."


DEFAULTS: dict[str, Any] = DefaultSettings()._asdict()

IMPORT_STRINGS: set[Union[bytes, str]] = set()
REMOVED_SETTINGS: set[str] = set()

gdx_settings = SettingsHolder(
    setting_name=SETTING_NAME,
    defaults=DEFAULTS,
    import_strings=IMPORT_STRINGS,
    removed_settings=REMOVED_SETTINGS,
)

reload_my_settings = reload_settings(SETTING_NAME, gdx_settings)
setting_changed.connect(reload_my_settings)
