from graphene_django_extensions import DjangoNode
from graphene_django_extensions.permissions import AllowAuthenticated
from tests.example.filtersets import ExampleFilterSet
from tests.example.models import (
    Example,
    ForwardManyToMany,
    ForwardManyToOne,
    ForwardOneToOne,
    ReverseManyToMany,
    ReverseOneToMany,
    ReverseOneToOne,
)


class ExampleNode(DjangoNode):
    class Meta:
        model = Example
        fields = [
            "pk",
            "name",
            "number",
            "email",
            "example_state",
            "forward_one_to_one_field",
            "forward_many_to_one_field",
            "forward_many_to_many_fields",
            "reverse_one_to_one_rel",
            "reverse_one_to_many_rels",
            "reverse_many_to_many_rels",
        ]
        permission_classes = [
            AllowAuthenticated,
        ]
        restricted_fields = {
            "email": lambda user: user.is_superuser,
        }
        filterset_class = ExampleFilterSet


class ForwardOneToOneNode(DjangoNode):
    class Meta:
        model = ForwardOneToOne
        fields = [
            "pk",
            "name",
            "example_rel",
        ]


class ForwardManyToOneNode(DjangoNode):
    class Meta:
        model = ForwardManyToOne
        fields = [
            "pk",
            "name",
            "example_rels",
        ]


class ForwardManyToManyNode(DjangoNode):
    class Meta:
        model = ForwardManyToMany
        fields = [
            "pk",
            "name",
            "example_rels",
        ]


class ReverseOneToOneNode(DjangoNode):
    class Meta:
        model = ReverseOneToOne
        fields = [
            "pk",
            "name",
            "example_field",
        ]


class ReverseOneToManyNode(DjangoNode):
    class Meta:
        model = ReverseOneToMany
        fields = [
            "pk",
            "name",
            "example_field",
        ]


class ReverseManyToManyNode(DjangoNode):
    class Meta:
        model = ReverseManyToMany
        fields = [
            "pk",
            "name",
            "example_fields",
        ]
