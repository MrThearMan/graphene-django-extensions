from django.core import validators
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from example_project.app.models import Example, ForwardManyToMany, ForwardOneToOne
from example_project.app.nodes import ExampleNode, ForwardManyToManyNode, ForwardOneToOneNode
from graphene_django_extensions import NestingModelSerializer


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
            "duration",
            "example_property",
            "forward_one_to_one_field",
            "forward_many_to_one_field",
            "forward_many_to_many_fields",
        ]
        node = ExampleNode

    def validate_number(self, value: int) -> int:
        if value < 0:
            msg = "Number must be positive."
            raise ValidationError(msg)
        return value


class ExampleCustomInputSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)


class ExampleCustomOutputSerializer(serializers.Serializer):
    pk = serializers.IntegerField()


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()


class ImageInputSerializer(serializers.Serializer):
    image = serializers.ImageField(
        write_only=True,
        required=True,
        validators=[validators.validate_image_file_extension],
    )


class ImageOutputSerializer(serializers.Serializer):
    name = serializers.CharField(read_only=True)
    success = serializers.BooleanField(read_only=True)
