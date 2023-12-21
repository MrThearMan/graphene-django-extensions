from __future__ import annotations

from typing import TYPE_CHECKING

from graphql.language.ast import (
    BooleanValueNode,
    ConstListValueNode,
    ConstObjectValueNode,
    EnumValueNode,
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
    from .typing import Any, GQLInfo

__all__ = [
    "get_nested",
    "get_filters_from_info",
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
    filters: dict[str, Any] = {}

    for field in info.operation.selection_set.selections:
        if not isinstance(field, FieldNode):  # pragma: no cover
            continue
        for argument in field.arguments:
            filters[argument.name.value] = _get_filter_argument(argument.value, info.variable_values)

    return filters


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
