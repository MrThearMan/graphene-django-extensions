import graphene

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


schema = graphene.Schema(query=Query)
