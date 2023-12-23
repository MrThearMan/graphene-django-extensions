from __future__ import annotations

from typing import TYPE_CHECKING

from graphene.types.mutation import MutationOptions
from graphene_django.types import DjangoObjectTypeOptions

if TYPE_CHECKING:
    from django.db import models
    from rest_framework.serializers import ModelSerializer

    from graphene_django_extensions.permissions import BasePermission

    from .bases import DjangoMutation, DjangoNode
    from .typing import FieldNameStr, Literal, Sequence


__all__ = [
    "DjangoNodeOptions",
    "DjangoMutationOptions",
]


class DjangoNodeOptions(DjangoObjectTypeOptions):
    def __init__(
        self,
        class_type: type[DjangoNode],
        permission_classes: Sequence[type[BasePermission]] = (),
    ) -> None:
        self.permission_classes = permission_classes
        super().__init__(class_type)


class DjangoMutationOptions(MutationOptions):
    def __init__(  # noqa: PLR0913
        self,
        class_type: type[DjangoMutation],
        lookup_field: FieldNameStr | None,
        model_class: type[models.Model] | None,
        serializer_class: type[ModelSerializer] | None,
        output_serializer_class: type[ModelSerializer] | None,
        permission_classes: Sequence[type[BasePermission]],
        model_operation: Literal["create", "update", "delete", "custom"],
    ) -> None:
        self.lookup_field = lookup_field
        self.model_class = model_class
        self.model_operation = model_operation
        self.serializer_class = serializer_class
        self.output_serializer_class = output_serializer_class
        self.permission_classes = permission_classes
        super().__init__(class_type)
