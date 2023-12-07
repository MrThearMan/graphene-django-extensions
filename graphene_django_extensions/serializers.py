from __future__ import annotations

from typing import TYPE_CHECKING, Any, Union

from django.shortcuts import get_object_or_404
from rest_framework.serializers import ListSerializer, ModelSerializer

from .fields import IntegerPrimaryKeyField
from .typing import AnyUser, SerializerMeta
from .utils import RelatedFieldInfo, get_rel_field_info, handle_related

if TYPE_CHECKING:
    from django.db.models import Model
    from rest_framework.fields import Field

__all__ = [
    "BaseModelSerializer",
]


RelatedSerializer = Union["BaseModelSerializer", ListSerializer]


class BaseModelSerializer(ModelSerializer):
    """
    ModelSerializer that contains logic for updating and creating related models
    when they are included as nested serializer fields:

    ```
    class SubSerializer(ModelSerializer):
        class Meta:
            model = Sub
            fields = ["pk", "field"]

    class MainSerializer(ModelSerializer):
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
            "field": "value",
        },
    }
    ```

    This will create the Main entity and the Sub entity,
    and set the Sub entity's 'main' field to the Main entity.

    If instead this is used:

    ```
    {
        "pk": 1,
        "sub_entities": {
            "pk": 2,
        },
    }
    ```

    This will create the Main entity and link an existing Sub entity with pk=2 to it.
    If the Sub entity does not exist, a 404 error will be raised.

    If the 'pk' field is included with some other fields, the Sub entity will also be updated:

    ```
    {
        "pk": 1,
        "sub_entities": {
            "pk": 2,
            "field": "value",
        },
    }
    ```

    For "to_many" relations, the serializer field must be a ListSerializer:

    ```
    class MainSerializer(serializers.ModelSerializer):
        sub_entry = SubSerializer(many=True)
    ```

    Same logic applies for "to_many" relations, but if the relation is a 'one_to_many' relation,
    and the relation is updated, any existing related entities that were not included in the request
    will be deleted.

    ```
    {
        "pk": 1,
        "sub_entities": [
            # If pk=1 was previously linked to the main entity, it will be deleted if not included
            # {"pk": 1},
            {"pk": 2},
            {"field": "value"},  # can also add new entities in the same request
        ],
    }
    ```
    """

    instance: Model  # use this to hint the instance model type in subclasses
    serializer_related_field = IntegerPrimaryKeyField  # related fields defined in Meta are integers by default

    class Meta(SerializerMeta):
        pass

    def get_or_default(self, field: str, attrs: dict[str, Any]) -> Any:
        default = self.Meta.model._meta.get_field(field).default
        default = getattr(self.instance, field, default)
        return attrs.get(field, default)

    @property
    def request_user(self) -> AnyUser:
        return self.context["request"].user

    def get_update_or_create(self, data: dict[str, Any] | None) -> Model | None:
        if data is None:
            return None

        pk = data.pop("pk", None)
        if pk is not None:
            instance = get_object_or_404(self.Meta.model, pk=pk)
            if not data:
                return instance
            return self.update(instance, data)

        return self.create(data)

    @handle_related
    def create(self, validated_data: dict[str, Any]) -> Model:
        """Create a new instance of the model, while also handling related models."""
        return self.Meta.model._default_manager.create(**validated_data)

    @handle_related
    def update(self, instance: Model, validated_data: dict[str, Any]) -> Model:
        """Update an existing instance of the model, while also handling related models."""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def _prepare_related(self, validated_data: dict[str, Any]) -> dict[str, RelatedSerializer]:
        """
        Prepare related models defined using BaseModelSerializers.
        Forward 'one-to-one' and 'many-to-one' related entities will be fetched, updated, or created.
        Other related entities will be saved to be handled after the main model is saved using '_handle_to_many'.
        """
        related_serializers: dict[str, RelatedSerializer] = {}
        related_info = get_rel_field_info(self.Meta.model)

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
            if isinstance(field, BaseModelSerializer):
                if related_field_info.reverse and related_field_info.one_to_one:
                    field.initial_data = validated_data.pop(name, None)
                    if field.initial_data is None:
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
            elif isinstance(field, ListSerializer) and isinstance(field.child, BaseModelSerializer):
                field.initial_data = validated_data.pop(name, None)
                if field.initial_data is None:
                    continue

                field.related_field_info = related_field_info
                related_serializers[name] = field

        return related_serializers

    def _handle_related(self, instance: Model, related_serializers: dict[str, RelatedSerializer]) -> None:
        """
        Handle creating or updating related models after the main model.
        Delete any existing 'one_to_many' entities that were untouched in this request.
        Add any new 'many_to_many' entities that were not previously linked to the main model.
        """
        for field_name, serializer in related_serializers.items():
            rel_info: RelatedFieldInfo | None = getattr(serializer, "related_field_info", None)
            if rel_info is None:
                continue

            # Handle reverse one-to-one
            if isinstance(serializer, BaseModelSerializer):
                serializer.initial_data[rel_info.name] = instance
                serializer.get_update_or_create(serializer.initial_data)
                continue

            instances: list[Model] = []
            pks: list[Any] = []
            child_serializer: BaseModelSerializer = serializer.child

            for item in serializer.initial_data:
                if rel_info.one_to_many:
                    item[rel_info.name] = instance

                nested_instance = child_serializer.get_update_or_create(item)
                if nested_instance is None:
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
