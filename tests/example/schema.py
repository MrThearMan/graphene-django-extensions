import graphene

from tests.example.mutations import ExampleCreateMutation, ExampleDeleteMutation, ExampleUpdateMutation
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
    example = ExampleNode.Node()
    examples = ExampleNode.Connection()

    forward_one_to_one = ForwardOneToOneNode.Node()
    forward_many_to_one = ForwardManyToOneNode.Node()
    forward_many_to_many = ForwardManyToManyNode.Node()
    reverse_one_to_one = ReverseOneToOneNode.Node()
    reverse_many_to_one = ReverseOneToManyNode.Node()
    reverse_many_to_many = ReverseManyToManyNode.Node()


class Mutation(graphene.ObjectType):
    create_example = ExampleCreateMutation.Field()
    update_example = ExampleUpdateMutation.Field()
    delete_example = ExampleDeleteMutation.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
