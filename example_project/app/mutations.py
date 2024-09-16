from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any

from django.contrib.auth import get_user_model, login
from rest_framework.exceptions import ValidationError

from example_project.app.forms import ExampleForm, ExampleInputForm, ExampleOutputForm
from example_project.app.models import Example, ExampleState, ForwardManyToOne, ForwardOneToOne
from example_project.app.serializers import (
    ExampleCustomInputSerializer,
    ExampleCustomOutputSerializer,
    ExampleSerializer,
    ImageInputSerializer,
    ImageOutputSerializer,
    LoginSerializer,
)
from graphene_django_extensions import CreateMutation, DeleteMutation, UpdateMutation
from graphene_django_extensions.bases import DjangoMutation
from graphene_django_extensions.permissions import AllowAuthenticated

if TYPE_CHECKING:
    from graphene_django_extensions.typing import AnyUser, GQLInfo, Self

User = get_user_model()


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
            raise ValidationError({"number": "Number must be positive."})


class ExampleCustomMutation(DjangoMutation):
    class Meta:
        serializer_class = ExampleCustomInputSerializer
        output_serializer_class = ExampleCustomOutputSerializer
        permission_classes = [AllowAuthenticated]

    @classmethod
    def custom_mutation(cls, info: GQLInfo, input_data: dict[str, Any]) -> Self:
        input_data["number"] = 1
        input_data["email"] = "example@email.com"
        input_data["example_state"] = ExampleState.ACTIVE
        input_data["duration"] = datetime.timedelta(seconds=900)
        input_data["forward_one_to_one_field"] = ForwardOneToOne.objects.create(name="Test")
        input_data["forward_many_to_one_field"] = ForwardManyToOne.objects.create(name="Test")
        example = Example.objects.create(**input_data)
        return cls(pk=example.pk)


class ExampleFormMutation(CreateMutation):
    class Meta:
        form_class = ExampleForm


class ExampleFormCustomMutation(DjangoMutation):
    class Meta:
        form_class = ExampleInputForm
        output_form_class = ExampleOutputForm

    @classmethod
    def custom_mutation(cls, info: GQLInfo, input_data: dict[str, Any]) -> Self:
        input_data["number"] = 1
        input_data["email"] = "example@email.com"
        input_data["example_state"] = ExampleState.ACTIVE
        input_data["duration"] = datetime.timedelta(seconds=900)
        input_data["forward_one_to_one_field"] = ForwardOneToOne.objects.create(name="Test")
        input_data["forward_many_to_one_field"] = ForwardManyToOne.objects.create(name="Test")
        example = Example.objects.create(**input_data)
        return cls(pk=example.pk)


class LoginMutation(DjangoMutation):
    class Meta:
        serializer_class = LoginSerializer

    @classmethod
    def custom_mutation(cls, info: GQLInfo, input_data: dict[str, Any]) -> Self:
        try:
            user = User.objects.get(username=input_data["username"])
        except User.DoesNotExist:
            user = User.objects.create_user(username=input_data["username"], password="test_password")  # noqa: S106

        login(info.context, user)
        return cls()


class ImageMutation(DjangoMutation):
    class Meta:
        serializer_class = ImageInputSerializer
        output_serializer_class = ImageOutputSerializer

    @classmethod
    def custom_mutation(cls, info: GQLInfo, input_data: dict[str, Any]) -> Self:
        return cls(success=True, name=input_data["image"].name)
