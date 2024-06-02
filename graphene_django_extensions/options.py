from __future__ import annotations

from typing import TYPE_CHECKING

from graphene.types.mutation import MutationOptions
from query_optimizer.typing import OptimizedDjangoOptions

if TYPE_CHECKING:
    from django.db import models
    from django.forms import Form, ModelForm
    from rest_framework.serializers import ModelSerializer, Serializer

    from graphene_django_extensions.permissions import BasePermission

    from .bases import DjangoMutation
    from .typing import FieldNameStr, Literal, Sequence


__all__ = [
    "DjangoMutationOptions",
    "DjangoNodeOptions",
]


class DjangoNodeOptions(OptimizedDjangoOptions):
    permission_classes: Sequence[type[BasePermission]] = ()


class DjangoMutationOptions(MutationOptions):
    def __init__(  # noqa: PLR0913
        self,
        class_type: type[DjangoMutation],
        lookup_field: FieldNameStr | None,
        model_class: type[models.Model] | None,
        serializer_class: type[ModelSerializer | Serializer] | None,
        output_serializer_class: type[ModelSerializer | Serializer] | None,
        form_class: type[ModelForm | Form] | None,
        output_form_class: type[ModelForm | Form] | None,
        permission_classes: Sequence[type[BasePermission]],
        model_operation: Literal["create", "update", "delete", "custom"],
    ) -> None:
        self.lookup_field = lookup_field
        self.model_class = model_class
        self.model_operation = model_operation
        self.serializer_class = serializer_class
        self.output_serializer_class = output_serializer_class
        self.form_class = form_class
        self.output_form_class = output_form_class
        self.permission_classes = permission_classes
        super().__init__(class_type)
