from __future__ import annotations

from typing import TYPE_CHECKING

from graphql.language.ast import (
    BooleanValueNode,
    ConstListValueNode,
    ConstObjectValueNode,
    EnumValueNode,
    ExecutableDefinitionNode,
    FieldNode,
    FloatValueNode,
    IntValueNode,
    ListValueNode,
    ObjectValueNode,
    StringValueNode,
    ValueNode,
    VariableNode,
)

if TYPE_CHECKING:
    from django.db import models

    from .typing import Any, GQLInfo, Sequence

__all__ = [
    "get_fields_from_info",
    "get_filters_from_info",
    "get_nested",
    "add_translatable_fields",
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
        except IndexError:
            obj = None
        return get_nested(obj, *args, default=default)

    obj = obj or {}
    return get_nested(obj.get(arg), *args, default=default)


def get_filters_from_info(info: GQLInfo) -> dict[str, Any]:
    """Find filter arguments in the GraphQL query and return them as a dict."""
    return _get_arguments(info.operation, info.variable_values)


def _get_arguments(field: ExecutableDefinitionNode | FieldNode, variable_values: dict[str, Any]) -> dict[str, Any]:
    arguments: dict[str, Any] = {}
    for selection in field.selection_set.selections:
        if not isinstance(selection, FieldNode):  # pragma: no cover
            continue

        for argument in selection.arguments:
            args = arguments.setdefault(selection.name.value, {})
            args[argument.name.value] = _get_filter_argument(argument.value, variable_values)

        if selection.selection_set is not None:
            result = _get_arguments(selection, variable_values)
            if result:
                args = arguments.setdefault(selection.name.value, {})
                args.update(result)
    return arguments


def _get_filter_argument(value: ValueNode, variable_values: dict[str, Any]) -> Any:
    if isinstance(value, (IntValueNode, FloatValueNode, StringValueNode, BooleanValueNode, EnumValueNode)):
        return value.value
    if isinstance(value, (ListValueNode, ConstListValueNode)):
        return [_get_filter_argument(val, variable_values) for val in value.values]
    if isinstance(value, (ObjectValueNode, ConstObjectValueNode)):
        return {field.name.value: _get_filter_argument(field.value, variable_values) for field in value.fields}
    if isinstance(value, VariableNode):  # pragma: no cover
        return variable_values[value.name.value]

    msg = f"Unsupported ValueNode for filter argument type: '{type(value).__name__}'"  # pragma: no cover
    raise ValueError(msg)  # pragma: no cover


def get_fields_from_info(info: GQLInfo) -> dict[str, Any]:
    """Find selected fields from the GraphQL query and return them as a dict."""
    return _get_field_node(info.operation)


def _get_field_node(field: ExecutableDefinitionNode | FieldNode) -> dict[str, Any] | list[Any]:
    filters: list[Any] = []
    for selection in field.selection_set.selections:
        if not isinstance(selection, FieldNode):  # pragma: no cover
            continue
        if selection.selection_set is not None:
            filters.append({selection.name.value: _get_field_node(selection)})
        else:
            filters.append(selection.name.value)
    if len(filters) == 1 and isinstance(filters[0], dict):
        return filters[0]
    return filters


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
