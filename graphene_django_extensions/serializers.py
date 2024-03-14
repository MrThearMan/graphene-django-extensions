from __future__ import annotations

import dataclasses
from functools import wraps
from typing import TYPE_CHECKING

from django.db import IntegrityError, models, transaction
from django.db.models import NOT_PROVIDED
from graphene_django.types import ALL_FIELDS
from rest_framework.exceptions import ValidationError
from rest_framework.relations import ManyRelatedField, RelatedField
from rest_framework.serializers import ListSerializer, ModelSerializer

from .errors import get_constraint_message
from .fields import DurationField, EnumFriendlyChoiceField, IntegerPrimaryKeyField
from .model_operations import RelatedFieldInfo, get_object_or_404, get_related_field_info
from .typing import ParamSpec, SerializerMeta, TypeVar
from .utils import add_translatable_fields

if TYPE_CHECKING:
    from django.db.models import Model
    from rest_framework.fields import Field

    from .typing import Any, AnyUser, Callable, Self


__all__ = [
    "NestingModelSerializer",
]


@dataclasses.dataclass
class PreSaveInfo:
    field: Field
    initial_data: Any
    related_info: RelatedFieldInfo


class NotProvided:  # pragma: no cover
    def __bool__(self) -> bool:
        return False


NotProvided = NotProvided()


T = TypeVar("T")
P = ParamSpec("P")


def _related_pre_and_post_save(func: Callable[P, T]) -> Callable[P, T]:
    """Handle related models before and after creating or updating the main model."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> models.Model:
        self: NestingModelSerializer = args[0]
        validated_data = next((arg for arg in args if isinstance(arg, dict)), kwargs.get("validated_data"))
        if validated_data is None:  # pragma: no cover
            msg = "'validated_data' not found in args or kwargs"
            raise ValueError(msg)

        try:
            with transaction.atomic():
                related_serializers = self._pre_save(validated_data)
                instance = func(*args, **kwargs)
                if related_serializers:
                    self._post_save(instance, related_serializers)
        except IntegrityError as error:
            msg = get_constraint_message(error.args[0])
            raise ValidationError(msg) from error

        return instance

    return wrapper


class NestingModelSerializer(ModelSerializer):
    """
    ModelSerializer that contains logic for updating and creating related models
    when they are included as nested (list)serializer fields or (lists of) primary keys.
    """

    instance: Model  # Use this to hint the instance model type in subclasses
    serializer_related_field = IntegerPrimaryKeyField  # Related fields defined in Meta are integers by default
    serializer_choice_field = EnumFriendlyChoiceField  # Converts enums to string correctly
    serializer_field_mapping = ModelSerializer.serializer_field_mapping | {
        models.DurationField: DurationField,
    }

    class Meta(SerializerMeta):
        pass

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        if cls.Meta.fields != ALL_FIELDS:
            cls.Meta.fields = add_translatable_fields(cls.Meta.model, cls.Meta.fields)
        return super().__new__(cls, *args, **kwargs)

    def get_or_default(self, field: str, attrs: dict[str, Any]) -> Any:
        """
        Get field value from attrs, or if not found, use a default value from
        1) the serializer model instance, or 2) the model field.
        """
        default = self.Meta.model._meta.get_field(field).default
        default = getattr(self.instance, field, default)
        value = attrs.get(field, default)
        if value is NOT_PROVIDED:  # pragma: no cover
            return NotProvided  # This one is falsy
        return value

    @property
    def request_user(self) -> AnyUser:
        return self.context["request"].user

    def get_update_or_create(self, data: dict[str, Any] | None) -> Model | None:
        if data is None:  # pragma: no cover
            return None

        pk = data.pop("pk", None)
        if pk is not None:
            instance = get_object_or_404(self.Meta.model, pk=pk)
            if not data:
                return instance
            return self.update(instance, data)

        return self.create(data)

    @_related_pre_and_post_save
    def create(self, validated_data: dict[str, Any]) -> Model:
        """Create a new instance of the model, while also handling related models."""
        return self.Meta.model._default_manager.create(**validated_data)

    @_related_pre_and_post_save
    def update(self, instance: Model, validated_data: dict[str, Any]) -> Model:
        """Update an existing instance of the model, while also handling related models."""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def _pre_save(self, validated_data: dict[str, Any]) -> list[PreSaveInfo]:
        """
        Prepare related models defined using BaseModelSerializers.
        Forward 'one-to-one' and 'many-to-one' related entities will be fetched, updated, or created.
        Other related entities will be saved to be handled after the main model is saved using '_handle_to_many'.
        """
        pre_save_infos: list[PreSaveInfo] = []
        related_info = get_related_field_info(self.Meta.model)

        for name in list(validated_data):  # Copy keys so that we can pop from the original dict in the loop
            field: Field | None = self.fields.get(name, None)
            if field is None:
                continue

            related_field_info = related_info.get(name, None)
            if related_field_info is None:
                continue

            if related_field_info.one_to_one or related_field_info.many_to_one:
                info = self._pre_handle_to_one(field, related_field_info, validated_data, name)
                if info is not None:
                    pre_save_infos.append(info)

            elif related_field_info.one_to_many or related_field_info.many_to_many:
                info = self._pre_handle_to_many(field, related_field_info, validated_data, name)
                if info is not None:
                    pre_save_infos.append(info)

        return pre_save_infos

    def _pre_handle_to_one(
        self,
        field: Field,
        related_info: RelatedFieldInfo,
        validated_data: dict[str, Any],
        key: str,
    ) -> PreSaveInfo | None:
        initial_data: Any = validated_data.pop(key, None)
        if related_info.reverse:
            return PreSaveInfo(field=field, initial_data=initial_data, related_info=related_info)
        if isinstance(field, NestingModelSerializer):
            validated_data[key] = field.get_update_or_create(initial_data)
        else:
            validated_data[key] = initial_data
        return None

    def _pre_handle_to_many(
        self,
        field: Field,
        related_info: RelatedFieldInfo,
        validated_data: dict[str, Any],
        key: str,
    ) -> PreSaveInfo | None:
        initial_data: Any = validated_data.pop(key, None)
        if initial_data is None:  # pragma: no cover
            return None
        return PreSaveInfo(field=field, initial_data=initial_data, related_info=related_info)

    def _post_save(self, instance: Model, pre_save_info: list[PreSaveInfo]) -> None:
        """
        Handle creating or updating related models after the main model.
        Delete any existing 'one_to_many' entities that were untouched in this request.
        Add any new 'many_to_many' entities that were not previously linked to the main model.
        """
        for info in pre_save_info:
            # Handle reverse one-to-one
            if info.related_info.one_to_one and info.related_info.reverse:
                self._post_handle_reverse_one_to_one(instance, info)
            elif info.related_info.one_to_many:
                self._post_handle_one_to_many(instance, info)
            elif info.related_info.many_to_many:
                self._post_handle_many_to_many(instance, info)

    def _post_handle_reverse_one_to_one(self, instance: Model, info: PreSaveInfo) -> None:
        if info.initial_data is None:  # pragma: no cover
            related_instance = getattr(instance, info.related_info.field_name, None)
            if related_instance is not None:
                setattr(related_instance, info.related_info.related_name, None)
                related_instance.save()
            return

        if isinstance(info.field, NestingModelSerializer):
            info.initial_data[info.related_info.related_name] = instance
            info.field.get_update_or_create(info.initial_data)
            return

        if isinstance(info.field, RelatedField):
            setattr(info.initial_data, info.related_info.related_name, instance)
            info.initial_data.save()
            return

    def _post_handle_one_to_many(self, instance: Model, info: PreSaveInfo) -> None:
        if isinstance(info.field, ListSerializer) and isinstance(info.field.child, NestingModelSerializer):
            pks: list[Any] = []

            for initial_data in info.initial_data:
                initial_data[info.related_info.related_name] = instance
                nested_instance = info.field.child.get_update_or_create(initial_data)
                if nested_instance is not None:
                    pks.append(nested_instance.pk)

            # Delete related objects that were not created or modified.
            selector = {info.related_info.related_name: instance}
            info.field.child.Meta.model.objects.filter(**selector).exclude(pk__in=pks).delete()
            return

        if isinstance(info.field, ManyRelatedField):
            getattr(instance, info.related_info.field_name).set(info.initial_data)
            return

    def _post_handle_many_to_many(self, instance: Model, info: PreSaveInfo) -> None:
        if isinstance(info.field, ListSerializer) and isinstance(info.field.child, NestingModelSerializer):
            instances: list[Model] = []

            for item in info.initial_data:
                nested_instance = info.field.child.get_update_or_create(item)
                if nested_instance is not None:
                    instances.append(nested_instance)

            # Add related objects that were not previously linked to the main model.
            getattr(instance, info.related_info.field_name).set(instances)
            return

        if isinstance(info.field, ManyRelatedField):
            getattr(instance, info.related_info.field_name).set(info.initial_data)
            return

    def get_fields(self) -> dict[str, Field]:
        fields = super().get_fields()
        # Add the model field enum to `EnumFriendlyChoiceField`
        # if the enum was not explicitly defined in the serializer field.
        # (e.g. field created automatically based on `serializer_choice_field`)
        # This is used for mutation input enum naming.
        for name, field in fields.items():
            if hasattr(field, "enum") and field.enum is None:
                model_field = self.Meta.model._meta.get_field(name)
                field.enum = getattr(model_field, "enum", None)
        return fields
