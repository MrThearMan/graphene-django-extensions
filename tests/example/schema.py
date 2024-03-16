from typing import Any

import graphene

from graphene_django_extensions.typing import GQLInfo
from tests.example.models import Example
from tests.example.mutations import (
    ExampleCreateMutation,
    ExampleCustomMutation,
    ExampleDeleteMutation,
    ExampleFormCustomMutation,
    ExampleFormMutation,
    ExampleUpdateMutation,
    ImageMutation,
    LoginMutation,
)
from tests.example.nodes import (
    ExampleNode,
    ForwardManyToManyNode,
    ForwardManyToOneNode,
    ForwardOneToOneNode,
    ReverseManyToManyNode,
    ReverseOneToManyNode,
    ReverseOneToOneNode,
)


class Query(graphene.ObjectType):
    example_item = ExampleNode.Field()
    example_items = ExampleNode.ListField()
    example = ExampleNode.Node()
    examples = ExampleNode.Connection()

    forward_one_to_one = ForwardOneToOneNode.Node()
    forward_many_to_one = ForwardManyToOneNode.Node()
    forward_many_to_many = ForwardManyToManyNode.Node()
    reverse_one_to_one = ReverseOneToOneNode.Node()
    reverse_many_to_one = ReverseOneToManyNode.Node()
    reverse_many_to_many = ReverseManyToManyNode.Node()

    def resolve_example_item(self, info: GQLInfo, **kwargs: Any) -> Example | None:
        return Example.objects.first()

    def resolve_example_items(self, info: GQLInfo, **kwargs: Any) -> list[Example]:
        return Example.objects.all()


class Mutation(graphene.ObjectType):
    create_example = ExampleCreateMutation.Field()
    update_example = ExampleUpdateMutation.Field()
    delete_example = ExampleDeleteMutation.Field()
    custom_example = ExampleCustomMutation.Field()

    form_mutation = ExampleFormMutation.Field()
    form_custom_mutation = ExampleFormCustomMutation.Field()
    login = LoginMutation.Field()
    image_mutation = ImageMutation.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
