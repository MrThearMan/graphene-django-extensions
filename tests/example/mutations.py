from typing import Any

from rest_framework.exceptions import ValidationError

from graphene_django_extensions import CreateMutation, DeleteMutation, UpdateMutation
from graphene_django_extensions.bases import DjangoMutation
from graphene_django_extensions.permissions import AllowAuthenticated
from graphene_django_extensions.typing import AnyUser, GQLInfo, Self
from tests.example.forms import ExampleForm, ExampleInputForm, ExampleOutputForm
from tests.example.models import Example, ForwardManyToOne, ForwardOneToOne, State
from tests.example.serializers import ExampleCustomInputSerializer, ExampleCustomOutputSerializer, ExampleSerializer


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
        serializer_class = ExampleCustomInputSerializer
        output_serializer_class = ExampleCustomOutputSerializer
        permission_classes = [AllowAuthenticated]

    @classmethod
    def custom_mutation(cls, info: GQLInfo, **kwargs: Any) -> Self:
        kwargs["number"] = 1
        kwargs["email"] = "example@email.com"
        kwargs["state"] = State.ACTIVE
        kwargs["forward_one_to_one_field"] = ForwardOneToOne.objects.create(name="Test")
        kwargs["forward_many_to_one_field"] = ForwardManyToOne.objects.create(name="Test")
        example = Example.objects.create(**kwargs)
        return cls(pk=example.pk)


class ExampleFormMutation(CreateMutation):
    class Meta:
        form_class = ExampleForm


class ExampleFormCustomMutation(DjangoMutation):
    class Meta:
        form_class = ExampleInputForm
        output_form_class = ExampleOutputForm

    @classmethod
    def custom_mutation(cls, info: GQLInfo, **kwargs: Any) -> Self:
        kwargs["number"] = 1
        kwargs["email"] = "example@email.com"
        kwargs["state"] = State.ACTIVE
        kwargs["forward_one_to_one_field"] = ForwardOneToOne.objects.create(name="Test")
        kwargs["forward_many_to_one_field"] = ForwardManyToOne.objects.create(name="Test")
        example = Example.objects.create(**kwargs)
        return cls(pk=example.pk)
