from typing import Any

import graphene
from rest_framework.exceptions import ValidationError

from graphene_django_extensions import CreateMutation, DeleteMutation, UpdateMutation
from graphene_django_extensions.bases import DjangoMutation
from graphene_django_extensions.permissions import AllowAuthenticated
from graphene_django_extensions.typing import AnyUser, GQLInfo, Self
from tests.example.models import Example, ForwardManyToOne, ForwardOneToOne, State
from tests.example.serializers import ExampleSerializer


class ExampleCreateMutation(CreateMutation):
    class Meta:
        serializer_class = ExampleSerializer
        permission_classes = [AllowAuthenticated]


class ExampleUpdateMutation(UpdateMutation):
    class Meta:
        serializer_class = ExampleSerializer
        permission_classes = [AllowAuthenticated]


class ExampleDeleteMutation(DeleteMutation):
    class Meta:
        model = Example
        permission_classes = [AllowAuthenticated]

    @classmethod
    def validate_deletion(cls, instance: Example, user: AnyUser) -> None:
        if instance.number < 0:
            raise ValidationError("Number must be positive.")


class ExampleCustomMutation(DjangoMutation):
    class Meta:
        input_fields = {
            "name": graphene.String(required=True),
        }
        output_fields = {
            "pk": graphene.ID(),
        }

    @classmethod
    def custom_model_operation(cls, root: Example, info: GQLInfo, **kwargs: Any) -> Self:
        kwargs["number"] = 1
        kwargs["email"] = "example@email.com"
        kwargs["state"] = State.ACTIVE
        kwargs["forward_one_to_one_field"] = ForwardOneToOne.objects.create(name="Test")
        kwargs["forward_many_to_one_field"] = ForwardManyToOne.objects.create(name="Test")
        example = Example.objects.create(**kwargs)
        return cls(pk=example.pk)
