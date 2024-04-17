import contextlib

from django.db.models import Field, Model
from graphene.types.definitions import GrapheneObjectType
from graphene.utils.str_converters import to_snake_case
from graphql import FieldNode
from query_optimizer.ast import GraphQLASTWalker
from query_optimizer.typing import ToManyField, ToOneField

from graphene_django_extensions.typing import GQLInfo

from .typing import Any

__all__ = [
    "get_fields_selections",
]


def get_fields_selections(info: GQLInfo, model: type[Model]) -> list[Any]:
    """Compile filter information included in the GraphQL query."""
    compiler = FieldSelectionCompiler(info, model)
    compiler.run()
    return compiler.field_selections[0][to_snake_case(info.field_name)]


class FieldSelectionCompiler(GraphQLASTWalker):
    """Class for compiling filtering information from a GraphQL query."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.field_selections: list[Any] = []
        super().__init__(*args, **kwargs)

    def handle_query_class(self, field_type: GrapheneObjectType, field_node: FieldNode) -> None:
        with self.child_selections(field_node):
            return super().handle_query_class(field_type, field_node)

    def handle_normal_field(self, field_type: GrapheneObjectType, field_node: FieldNode, field: Field) -> None:
        self.field_selections.append(to_snake_case(field_node.name.value))

    def handle_custom_field(self, field_type: GrapheneObjectType, field_node: FieldNode) -> None:
        self.field_selections.append(to_snake_case(field_node.name.value))

    def handle_to_one_field(
        self,
        field_type: GrapheneObjectType,
        field_node: FieldNode,
        related_field: ToOneField,
        related_model: type[Model],
    ) -> None:
        with self.child_selections(field_node):
            return super().handle_to_many_field(field_type, field_node, related_field, related_model)

    def handle_to_many_field(
        self,
        field_type: GrapheneObjectType,
        field_node: FieldNode,
        related_field: ToManyField,
        related_model: type[Model],
    ) -> None:
        with self.child_selections(field_node):
            return super().handle_to_one_field(field_type, field_node, related_field, related_model)

    @contextlib.contextmanager
    def child_selections(self, field_node: FieldNode) -> None:
        field_name = to_snake_case(field_node.name.value)
        selections: list[Any] = []
        orig_selections = self.field_selections
        try:
            self.field_selections = selections
            yield
        finally:
            self.field_selections = orig_selections
            if selections:
                self.field_selections.append({field_name: selections})
