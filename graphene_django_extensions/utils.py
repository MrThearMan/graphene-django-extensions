from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING

from graphene import Connection
from graphene.utils.str_converters import to_snake_case
from graphql import get_argument_values
from graphql.execution.execute import get_field_def
from graphql.language.ast import ExecutableDefinitionNode, FieldNode, SelectionNode
from query_optimizer.ast import get_underlying_type

from .constants import Operation
from .settings import gdx_settings
from .typing import GraphQLFilterInfo, StrEnum

if TYPE_CHECKING:
    from django.db import models
    from graphql import GraphQLField, GraphQLObjectType, GraphQLSchema

    from .typing import Any, GQLInfo, Iterable, Sequence

__all__ = [
    "get_fields_from_info",
    "get_filter_info",
    "get_nested",
    "add_translatable_fields",
    "get_operator_enum",
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


def get_filter_info(info: GQLInfo) -> dict[str, Any]:
    """Find filter arguments from the GraphQL query."""
    args = _get_arguments(info.field_nodes, info.variable_values, info.parent_type, info.schema)
    if not args:
        return {}
    return args[to_snake_case(info.field_name)]


def _get_arguments(
    field_nodes: Iterable[FieldNode | SelectionNode],
    variable_values: dict[str, Any],
    parent: GraphQLObjectType,
    schema: GraphQLSchema,
) -> dict[str, GraphQLFilterInfo]:
    arguments: dict[str, GraphQLFilterInfo] = {}
    for field_node in field_nodes:
        if not isinstance(field_node, FieldNode):  # pragma: no cover
            continue

        field_def: GraphQLField | None = get_field_def(schema, parent, field_node)
        if field_def is None:  # pragma: no cover
            continue

        name = to_snake_case(field_node.name.value)
        filters = get_argument_values(type_def=field_def, node=field_node, variable_values=variable_values)

        new_parent = get_underlying_type(field_def.type)

        # If the field is a connection, we need to go deeper to get the actual field
        if issubclass(getattr(new_parent, "graphene_type", type(None)), Connection):
            field_def = new_parent.fields["edges"]
            new_parent = get_underlying_type(field_def.type)
            field_def = new_parent.fields["node"]
            new_parent = get_underlying_type(field_def.type)
            field_node = field_node.selection_set.selections[0].selection_set.selections[0]  # noqa: PLW2901

        arguments[name] = info = GraphQLFilterInfo(name=new_parent.name, filters=filters, children={})

        if field_node.selection_set is not None:
            result = _get_arguments(field_node.selection_set.selections, variable_values, new_parent, schema)
            if result:
                info["children"] = result

    return {name: field for name, field in arguments.items() if field["filters"] or field["children"]}


def get_fields_from_info(info: GQLInfo) -> list[dict[str, Any]]:
    """Find selected fields from the GraphQL query and return them as a list of dicts."""
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


@cache
def get_operator_enum() -> type[Operation]:
    if not gdx_settings.EXTEND_USER_DEFINED_FILTER_OPERATIONS:  # pragma: no cover
        return Operation

    current_members: dict[str, str] = {key: value.value for key, value in Operation._member_map_.items()}
    for operator in gdx_settings.EXTEND_USER_DEFINED_FILTER_OPERATIONS:
        current_members[operator.upper()] = operator.upper()

    return StrEnum(Operation.__name__, current_members)  # type: ignore[return-value]
