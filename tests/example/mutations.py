from graphene_django_extensions import BaseModelSerializer, CreateMutation, DeleteMutation, UpdateMutation
from tests.example.models import Example, ForwardManyToOne, ForwardOneToOne
from tests.example.nodes import ExampleNode, ForwardManyToOneNode, ForwardOneToOneNode


class ForwardOneToOneSerializer(BaseModelSerializer):
    class Meta:
        model = ForwardOneToOne
        fields = ["pk", "name"]
        node = ForwardOneToOneNode


class ForwardManyToOneSerializer(BaseModelSerializer):
    class Meta:
        model = ForwardManyToOne
        fields = ["pk", "name"]
        node = ForwardManyToOneNode


class ExampleSerializer(BaseModelSerializer):
    forward_one_to_one_field = ForwardOneToOneSerializer()
    forward_many_to_one_field = ForwardManyToOneSerializer()

    class Meta:
        model = Example
        fields = [
            "pk",
            "name",
            "number",
            "email",
            "forward_one_to_one_field",
            "forward_many_to_one_field",
        ]
        node = ExampleNode


class ExampleCreateMutation(CreateMutation):
    class Meta:
        serializer_class = ExampleSerializer


class ExampleUpdateMutation(UpdateMutation):
    class Meta:
        serializer_class = ExampleSerializer


class ExampleDeleteMutation(DeleteMutation):
    class Meta:
        model = Example
