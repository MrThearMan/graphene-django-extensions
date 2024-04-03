from graphene_django_extensions import DjangoNode
from graphene_django_extensions.permissions import AllowAuthenticated
from tests.example.filtersets import (
    ExampleFilterSet,
    ForwardManyToManyFilterSet,
    ForwardManyToOneFilterSet,
    ForwardOneToOneFilterSet,
    ReverseManyToManyFilterSet,
    ReverseOneToManyFilterSet,
    ReverseOneToOneFilterSet,
)
from tests.example.models import (
    Example,
    ForwardManyToMany,
    ForwardManyToOne,
    ForwardOneToOne,
    ReverseManyToMany,
    ReverseOneToMany,
    ReverseOneToOne,
)


class ForwardOneToOneNode(DjangoNode):
    class Meta:
        model = ForwardOneToOne
        fields = [
            "pk",
            "name",
            "example_rel",
        ]
        permission_classes = [AllowAuthenticated]
        filterset_class = ForwardOneToOneFilterSet


class ForwardManyToOneNode(DjangoNode):
    class Meta:
        model = ForwardManyToOne
        fields = [
            "pk",
            "name",
            "example_rels",
        ]
        permission_classes = [AllowAuthenticated]
        filterset_class = ForwardManyToOneFilterSet


class ForwardManyToManyNode(DjangoNode):
    class Meta:
        model = ForwardManyToMany
        fields = [
            "pk",
            "name",
            "example_rels",
        ]
        permission_classes = [AllowAuthenticated]
        filterset_class = ForwardManyToManyFilterSet


class ReverseOneToOneNode(DjangoNode):
    class Meta:
        model = ReverseOneToOne
        fields = [
            "pk",
            "name",
            "example_field",
        ]
        permission_classes = [AllowAuthenticated]
        filterset_class = ReverseOneToOneFilterSet


class ReverseOneToManyNode(DjangoNode):
    class Meta:
        model = ReverseOneToMany
        fields = [
            "pk",
            "name",
            "example_field",
        ]
        permission_classes = [AllowAuthenticated]
        filterset_class = ReverseOneToManyFilterSet


class ReverseManyToManyNode(DjangoNode):
    class Meta:
        model = ReverseManyToMany
        fields = [
            "pk",
            "name",
            "example_fields",
        ]
        permission_classes = [AllowAuthenticated]
        filterset_class = ReverseManyToManyFilterSet


class ExampleNode(DjangoNode):
    forward_one_to_one_field = ForwardOneToOneNode.RelatedField()
    forward_many_to_one_field = ForwardManyToOneNode.RelatedField()
    forward_many_to_many_fields = ForwardManyToManyNode.ListField()
    reverse_one_to_one_rel = ReverseOneToOneNode.RelatedField()
    reverse_one_to_many_rels = ReverseOneToManyNode.ListField()
    reverse_many_to_many_rels = ReverseManyToManyNode.Connection()

    class Meta:
        model = Example
        fields = [
            "pk",
            "name",
            "number",
            "email",
            "example_state",
            "duration",
            "forward_one_to_one_field",
            "forward_many_to_one_field",
            "forward_many_to_many_fields",
            "reverse_one_to_one_rel",
            "reverse_one_to_many_rels",
            "reverse_many_to_many_rels",
        ]
        permission_classes = [AllowAuthenticated]
        restricted_fields = {
            "email": lambda user: user.is_superuser,
        }
        filterset_class = ExampleFilterSet
