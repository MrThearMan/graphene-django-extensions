from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING

from django.db import IntegrityError, models, transaction
from graphene_django.types import ALL_FIELDS
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import ListSerializer, ModelSerializer

from .errors import get_constraint_message
from .fields import DurationField, EnumFriendlyChoiceField, IntegerPrimaryKeyField
from .model_operations import RelatedFieldInfo, get_object_or_404, get_related_field_info
from .typing import ParamSpec, SerializerMeta, TypeVar
from .utils import add_translatable_fields

if TYPE_CHECKING:
    from django.db.models import Model
    from rest_framework.fields import Field

    from .typing import Any, AnyUser, Callable, RelatedSerializer, Self


__all__ = [
    "NestingModelSerializer",
]


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
    when they are included as nested serializer fields:

    ```
    from graphene_django_extensions import NestingModelSerializer

    class SubSerializer(NestingModelSerializer):
        class Meta:
            model = Sub
            fields = ["pk", "field"]

    class MainSerializer(NestingModelSerializer):
        sub_entry = SubSerializer()

        class Meta:
            model = Main
            fields = ["pk", "sub_entry"]
    ```

    When using the above serializers with the following data:

    ```
    {
        "pk": 1,
        "sub_entities": {
            "field": "value"
        }
    }
    ```

    This will create the Main entity and the Sub entity,
    and set the Sub entity's 'main' field to the Main entity.

    If instead this is used:

    ```
    {
        "pk": 1,
        "sub_entities": {
            "pk": 2
        }
    }
    ```

    This will create the Main entity and link an existing Sub entity with pk=2 to it.
    If the Sub entity does not exist, a 404 error will be raised. If the sub entity
    is already linked to another Main entity, this will be a no-op.

    If the 'pk' field is included with some other fields, the Sub entity will also be updated:

    ```
    {
        "pk": 1,
        "sub_entities": {
            "pk": 2,
            "field": "value"
        }
    }
    ```

    For "to_many" relations, the serializer field must be a ListSerializer:

    ```
    class MainSerializer(NestingModelSerializer):
        sub_entry = SubSerializer(many=True)
    ```

    Same logic applies for "to_many" relations, but if the relation is a 'one_to_many' relation,
    and the relation is updated. Any existing related entities that were not included in the request
    will be deleted (e.g., `pk=1` could have been deleted here):

    ```
    {
        "pk": 1,
        "sub_entities": [
            {"pk": 2},
            {"field": "value"}
        ]
    }
    ```
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
        return attrs.get(field, default)

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

    def _pre_save(self, validated_data: dict[str, Any]) -> dict[str, RelatedSerializer]:
        """
        Prepare related models defined using BaseModelSerializers.
        Forward 'one-to-one' and 'many-to-one' related entities will be fetched, updated, or created.
        Other related entities will be saved to be handled after the main model is saved using '_handle_to_many'.
        """
        related_serializers: dict[str, RelatedSerializer] = {}
        related_info = get_related_field_info(self.Meta.model)

        for name in list(validated_data):  # Copy keys so that we can pop from the original dict in the loop
            field: Field | None = self.fields.get(name, None)
            if field is None:
                continue

            related_field_info = related_info.get(name, None)
            if related_field_info is None:
                continue

            # Handle relation types:
            #  - Forward one-to-one
            #  - Forward many-to-one
            #  - Reverse one-to-one
            if isinstance(field, NestingModelSerializer):
                if related_field_info.reverse and related_field_info.one_to_one:
                    field.initial_data = validated_data.pop(name, None)
                    if field.initial_data is None:  # pragma: no cover
                        continue

                    field.related_field_info = related_field_info
                    related_serializers[name] = field
                    continue

                rel_data = validated_data.pop(name, None)
                validated_data[name] = field.get_update_or_create(rel_data)

            # Handle relation types:
            #  - Reverse one-to-many
            #  - Reverse many-to-many
            #  - Forward many-to-many
            elif isinstance(field, ListSerializer) and isinstance(field.child, NestingModelSerializer):
                field.initial_data = validated_data.pop(name, None)
                if field.initial_data is None:  # pragma: no cover
                    continue

                field.related_field_info = related_field_info
                related_serializers[name] = field

        return related_serializers

    def _post_save(self, instance: Model, related_serializers: dict[str, RelatedSerializer]) -> None:
        """
        Handle creating or updating related models after the main model.
        Delete any existing 'one_to_many' entities that were untouched in this request.
        Add any new 'many_to_many' entities that were not previously linked to the main model.
        """
        for field_name, serializer in related_serializers.items():
            rel_info: RelatedFieldInfo | None = getattr(serializer, "related_field_info", None)
            if rel_info is None:  # pragma: no cover
                continue

            # Handle reverse one-to-one
            if isinstance(serializer, NestingModelSerializer):
                serializer.initial_data[rel_info.name] = instance
                serializer.get_update_or_create(serializer.initial_data)
                continue

            instances: list[Model] = []
            pks: list[Any] = []
            child_serializer: NestingModelSerializer = serializer.child

            for item in serializer.initial_data:
                if rel_info.one_to_many:
                    item[rel_info.name] = instance

                nested_instance = child_serializer.get_update_or_create(item)
                if nested_instance is None:  # pragma: no cover
                    continue

                if rel_info.one_to_many:
                    pks.append(nested_instance.pk)
                if rel_info.many_to_many:
                    instances.append(nested_instance)

            if rel_info.one_to_many:
                # Delete related objects that were not created or modified.
                child_serializer.Meta.model.objects.filter(**{rel_info.name: instance}).exclude(pk__in=pks).delete()

            if rel_info.many_to_many:
                # Add related objects that were not previously linked to the main model.
                getattr(instance, field_name).set(instances)

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
