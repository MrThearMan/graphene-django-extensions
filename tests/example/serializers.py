from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from graphene_django_extensions import NestingModelSerializer
from tests.example.models import Example, ForwardManyToMany, ForwardOneToOne
from tests.example.nodes import ExampleNode, ForwardManyToManyNode, ForwardOneToOneNode


class ForwardOneToOneSerializer(NestingModelSerializer):
    class Meta:
        model = ForwardOneToOne
        fields = ["pk", "name"]
        node = ForwardOneToOneNode


class ForwardManyToManySerializer(NestingModelSerializer):
    class Meta:
        model = ForwardManyToMany
        fields = ["pk", "name"]
        node = ForwardManyToManyNode


class ExampleSerializer(NestingModelSerializer):
    forward_one_to_one_field = ForwardOneToOneSerializer()
    forward_many_to_many_fields = ForwardManyToManySerializer(many=True, required=False)

    class Meta:
        model = Example
        fields = [
            "pk",
            "name",
            "number",
            "email",
            "example_state",
            "example_property",
            "forward_one_to_one_field",
            "forward_many_to_one_field",
            "forward_many_to_many_fields",
        ]
        node = ExampleNode

    def validate_number(self, value: int) -> int:
        if value < 0:
            raise ValidationError("Number must be positive.")
        return value


class ExampleCustomInputSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)


class ExampleCustomOutputSerializer(serializers.Serializer):
    pk = serializers.IntegerField()
