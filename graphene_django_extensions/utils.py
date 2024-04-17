from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING

from query_optimizer.filter_info import get_filter_info

from .constants import Operation
from .settings import gdx_settings
from .typing import StrEnum

if TYPE_CHECKING:
    from django.db import models

    from .typing import Any, Sequence

__all__ = [
    "get_nested",
    "add_translatable_fields",
    "get_operator_enum",
    "get_filter_info",
]


def get_nested(obj: dict | list | None, /, *args: str | int, default: Any = None) -> Any:
    """
    Get value from a nested structure containing dicts with string keys or lists,
    where the keys and list indices might not exist.

    1) `data["foo"][0]["bar"]["baz"]`
     - Might raise a `KeyError` or `IndexError` if any of the keys or indices don't exist.

    2) `get_nested(data, "foo", 0, "bar", "baz")`
     - Will return `None` (default) if any of the keys or indices don't exist.
    """
    if not args:
        return obj if obj is not None else default

    arg, args = args[0], args[1:]

    if isinstance(arg, int):
        obj = obj or []
        try:
            obj = obj[arg]
        except (IndexError, KeyError):
            obj = None
        return get_nested(obj, *args, default=default)

    obj = obj or {}
    try:
        return get_nested(obj.get(arg), *args, default=default)
    except AttributeError:
        obj = None
        return get_nested(obj, *args, default=default)


def add_translatable_fields(model: type[models.Model], fields: Sequence[str]) -> Sequence[str]:  # pragma: no cover
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
def get_operator_enum() -> type[Operation]:
    if not gdx_settings.EXTEND_USER_DEFINED_FILTER_OPERATIONS:  # pragma: no cover
        return Operation

    current_members: dict[str, str] = {key: value.value for key, value in Operation._member_map_.items()}
    for operator in gdx_settings.EXTEND_USER_DEFINED_FILTER_OPERATIONS:
        current_members[operator.upper()] = operator.upper()

    return StrEnum(Operation.__name__, current_members)  # type: ignore[return-value]
