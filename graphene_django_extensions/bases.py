from __future__ import annotations

from enum import Enum
from functools import partial
from typing import TYPE_CHECKING

import graphene
from django.core.exceptions import ValidationError as DjangoValidationError
from graphene import ClientIDMutation, Field, InputField
from graphene.types.resolver import attr_resolver
from graphene.types.utils import yank_fields_from_attrs
from graphene_django import DjangoConnectionField, DjangoListField, DjangoObjectType
from graphene_django.converter import convert_django_field
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.registry import get_global_registry
from graphene_django.rest_framework.mutation import fields_for_serializer
from graphene_django.settings import graphene_settings
from graphene_django.types import ALL_FIELDS, ErrorType
from graphene_django.utils import camelize, is_valid_django_model
from graphql_relay import to_global_id
from rest_framework.exceptions import ValidationError as SerializerValidationError
from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ListSerializer, ModelSerializer, as_serializer_error
from rest_framework.settings import api_settings

from .connections import Connection
from .converters import convert_serializer_fields_to_not_required
from .errors import flatten_errors
from .model_operations import get_model_lookup_field, get_object_or_404
from .options import DjangoMutationOptions, DjangoNodeOptions
from .permissions import AllowAny, BasePermission, restricted_field
from .settings import gdx_settings
from .typing import Fields, Sequence
from .utils import get_filters_from_info

if TYPE_CHECKING:
    from django.db import models
    from django.http import HttpRequest
    from graphene.relay.node import NodeField
    from graphene.types.mountedtype import MountedType
    from graphene.types.unmountedtype import UnmountedType

    from .typing import Any, AnyUser, FieldNameStr, GQLInfo, Literal, PermCheck, Self


__all__ = [
    "DjangoNode",
    "CreateMutation",
    "UpdateMutation",
    "DeleteMutation",
]


class DjangoNode(DjangoObjectType):
    """
    Custom base class for GraphQL-types that are backed by a Django model.
    Adds the following features to all types that inherit it:

    - Makes the `graphene.relay.Node` interface the default interface for the type.

    - Adds the `errors` list-field to the type for returning errors.

    - Adds the `totalCount` field the default Connection field for the type.

    - Adds the `filter_queryset` method that can be overridden to add additional filtering for both
      `get_queryset` and `get_node` query sets.

    - Adds convenience methods for creating fields/list-fields/nodes/connections for the type.

    - Adds the `pk` field and resolver to the type if present on Meta.fields.

    ---

    The following options can be set in the `Meta`-class.

    `model: type[Model]`

    - Required. The model class for the node.

    `fields: list[FieldNameStr] | Literal["__all__"]`

    - Required. The fields to include in the node. If `__all__` is used, all fields are included.

    `permission_classes: Sequence[type[BasePermission]]`

    - Optional. Set permission classes for the node. Defaults to (`AllowAny`,).

    `restricted_fields: dict[FieldNameStr, PermCheck]`

    - Optional. Adds permission checks to the resolvers of the fields as defined in the dict.
    """

    _meta: DjangoNodeOptions

    class Meta:
        abstract = True

    errors = graphene.List(ErrorType, description="May contain more than one error for same field.")

    @classmethod
    def Field(cls, **kwargs: Any) -> Field:  # noqa: N802
        return Field(cls, **kwargs)

    @classmethod
    def ListField(cls, **kwargs: Any) -> DjangoListField:  # noqa: N802
        return DjangoListField(cls, **kwargs)

    @classmethod
    def Node(cls, **kwargs: Any) -> NodeField:  # noqa: N802
        return graphene.relay.Node.Field(cls, **kwargs)

    @classmethod
    def Connection(cls, **kwargs: Any) -> DjangoFilterConnectionField | DjangoConnectionField:  # noqa: N802
        if cls._meta.filterset_class is None and cls._meta.filter_fields is None:
            return DjangoConnectionField(cls, **kwargs)  # pragma: no cover
        return DjangoFilterConnectionField(cls, **kwargs)

    @classmethod
    def filter_queryset(cls, queryset: models.QuerySet, info: GQLInfo) -> models.QuerySet:
        """Implement this method filter to the available rows from the model on this node."""
        return queryset

    @classmethod
    def __init_subclass_with_meta__(
        cls,
        model: type[models.Model] | None = None,
        fields: Fields | None = None,
        permission_classes: Sequence[type[BasePermission]] = (AllowAny,),
        restricted_fields: dict[FieldNameStr, PermCheck] | None = None,
        **options: Any,
    ) -> None:
        if model is None:  # pragma: no cover
            msg = "`Meta.model` is required."
            raise ValueError(msg)

        if not is_valid_django_model(model):  # pragma: no cover
            msg = f"`Meta.model` needs to be a Model-class, received: `{model}`."
            raise TypeError(msg)

        if fields is None:  # pragma: no cover
            msg = "`Meta.fields` is required."
            raise ValueError(msg)

        if not (fields == ALL_FIELDS or isinstance(fields, Sequence)):  # pragma: no cover
            msg = f"`Meta.fields` is should be a Sequence of field names or `{ALL_FIELDS}`, received: `{fields}`."
            raise TypeError(msg)

        if not hasattr(cls, "pk") and (fields == ALL_FIELDS or "pk" in fields):
            cls._add_pk_field(model)

        if restricted_fields is not None:
            cls._add_field_restrictions(fields, restricted_fields)

        _meta = DjangoNodeOptions(class_type=cls, permission_classes=permission_classes)
        options.setdefault("connection_class", Connection)
        options.setdefault("interfaces", (graphene.relay.Node,))

        super().__init_subclass_with_meta__(_meta=_meta, model=model, fields=fields, **options)

    @classmethod
    def _add_pk_field(cls, model: type[models.Model]) -> None:
        cls.pk = graphene.Int() if model._meta.pk.name == "id" else graphene.ID()
        cls.resolve_pk = cls.resolve_id

    @classmethod
    def _add_field_restrictions(cls, fields: Fields, restricted_fields: dict[FieldNameStr, PermCheck]) -> None:
        for field_name, check in restricted_fields.items():
            if fields != ALL_FIELDS and field_name not in fields:  # pragma: no cover
                msg = f"Field `{field_name}` not in `Meta.fields`."
                raise ValueError(msg)

            resolver = getattr(cls, f"resolve_{field_name}", None)
            if resolver is None:
                resolver = partial(attr_resolver, field_name, None)  # must be positional args!

            setattr(cls, f"resolve_{field_name}", restricted_field(check)(resolver))

    @classmethod
    def get_queryset(cls, queryset: models.QuerySet, info: GQLInfo) -> models.QuerySet:
        """Override `filter_queryset` instead of this method to add filtering of possible rows."""
        if not cls.has_filter_permissions(info):
            msg = gdx_settings.FILTER_PERMISSION_ERROR_MESSAGE
            raise PermissionError(msg)
        return cls.filter_queryset(queryset, info)

    @classmethod
    def get_node(cls, info: GQLInfo, pk: Any) -> models.Model | None:
        """Override `filter_queryset` instead of this method to add filtering of possible rows."""
        if not cls.has_node_permissions(info, pk):
            msg = gdx_settings.QUERY_PERMISSION_ERROR_MESSAGE
            raise PermissionError(msg)
        queryset = cls._meta.model.objects.filter(pk=pk)
        return cls.filter_queryset(queryset, info).first()

    @classmethod
    def has_filter_permissions(cls, info: GQLInfo) -> bool:
        """Check which permissions are required to access lists of this type."""
        filters = get_filters_from_info(info)
        return all(perm.has_filter_permission(info.context.user, filters) for perm in cls._meta.permission_classes)

    @classmethod
    def has_node_permissions(cls, info: GQLInfo, pk: Any) -> bool:
        """Check which permissions are required to access single items of this type."""
        filters = get_filters_from_info(info)
        return all(perm.has_node_permission(info.context.user, pk, filters) for perm in cls._meta.permission_classes)

    @classmethod
    def get_global_id(cls, pk: Any) -> str:
        """Get id used for `node` queries."""
        return to_global_id(cls.__name__, pk)


class DjangoMutation(ClientIDMutation):
    """
    Custom base class for GraphQL-mutations that are backed by a Django model.
    Adds the following features to all types that inherit it:

    - Adds the `errors` list-field to the type for returning errors.

    - For updates, converts all fields to optional fields, enabling partial updates.

    - Checks for missing object types for nested model serializer fields to avoid nebulous import order errors.

    - Can add permission checks via permission classes.

    - Formats errors raised from nested serializers to a compatible form.

    ---

    The following options can be set in the `Meta`-class.

    `model: type[models.Model]`

    - Required (delete only). Model class for the model the operation is performed on.

    `serializer_class: type[ModelSerializer]`

    - Required (create and update only). The serializer used for the mutation.

    `output_serializer_class: type[ModelSerializer]`

    - Optional. The serializer used for the output data. If not set, `serializer_class` is used.
      Serializer fields are modified so that all fields are optional, enabling partial updates.

    `permission_classes: Sequence[type[BasePermission]]`

    - Optional. Set permission classes for the mutation. Defaults to (`AllowAny`,).

    `lookup_field: str`

    - Optional. The field used for looking up the instance to be mutated. Defaults to the object's
      primary key, which is usually `id`. Note that the `lookup_field` attribute has to be available
      from the serializer's `Meta.fields` definition.
    """

    _meta: DjangoMutationOptions

    errors = graphene.List(ErrorType, description="May contain more than one error for same field.")

    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(  # noqa: PLR0913
        cls,
        lookup_field: FieldNameStr | None = None,
        model: type[models.Model] | None = None,
        serializer_class: type[ModelSerializer] | None = None,
        output_serializer_class: type[ModelSerializer] | None = None,
        permission_classes: Sequence[type[BasePermission]] = (AllowAny,),
        model_operation: Literal["create", "update", "delete", "custom"] = "custom",
        input_fields: dict[str, MountedType | UnmountedType] | None = None,
        output_fields: dict[str, MountedType | UnmountedType] | None = None,
        **options: Any,
    ) -> None:
        if model_operation == "delete":
            if model is None:  # pragma: no cover
                msg = "`Meta.model` is required."
                raise ValueError(msg)

            lookup_field = get_model_lookup_field(model, lookup_field)
            input_field = graphene.ID(required=True)
            if lookup_field != "pk":  # pragma: no cover
                input_field = convert_django_field(model._meta.get_field(lookup_field))

            input_fields = {lookup_field: input_field}
            output_fields = {"deleted": graphene.Boolean()}

        elif model_operation in ("create", "update"):
            if serializer_class is None:  # pragma: no cover
                msg = "`Meta.serializer_class` is required for create and update mutations."
                raise ValueError(msg)

            if not issubclass(serializer_class, ModelSerializer):  # pragma: no cover
                msg = "`Meta.serializer_class` needs to be a ModelSerializer."
                raise TypeError(msg)

            if model_operation == "update":
                serializer_class = convert_serializer_fields_to_not_required(serializer_class, lookup_field)

            serializer = output_serializer = serializer_class()

            if output_serializer_class is not None:  # pragma: no cover
                output_serializer = output_serializer_class()
            else:
                output_serializer_class = serializer_class

            _check_serializer_field_models_in_registry(cls, output_serializer)

            model: type[models.Model] = serializer_class.Meta.model
            lookup_field = get_model_lookup_field(model, lookup_field)

            input_fields = fields_for_serializer(
                serializer,
                only_fields=(),
                exclude_fields=(),
                is_input=True,
                lookup_field=lookup_field,
            )

            output_fields = fields_for_serializer(
                output_serializer,
                only_fields=(),
                exclude_fields=(),
                lookup_field=lookup_field,
            )

        elif cls.custom_model_operation == DjangoMutation.custom_model_operation:  # pragma: no cover
            msg = "`custom_model_operation` must be overridden in subclasses for custom model operations."
            raise ValueError(msg)

        input_fields = yank_fields_from_attrs(attrs=input_fields or {}, _as=InputField)
        output_fields = yank_fields_from_attrs(attrs=output_fields or {}, _as=Field)

        _meta = DjangoMutationOptions(
            class_type=cls,
            model_class=model,
            model_operation=model_operation,
            lookup_field=lookup_field,
            fields=output_fields,
            serializer_class=serializer_class,
            output_serializer_class=output_serializer_class,
            permission_classes=permission_classes,
        )

        super().__init_subclass_with_meta__(_meta=_meta, input_fields=input_fields, **options)

    @classmethod
    def has_permission(cls, root: Any, info: GQLInfo, input_data: dict[str, Any]) -> bool:
        filters = get_filters_from_info(info)
        user = info.context.user
        perms = cls._meta.permission_classes

        if cls._meta.model_operation == "create":
            return all(perm.has_create_permission(root, user, input_data, filters) for perm in perms)
        if cls._meta.model_operation == "update":
            return all(perm.has_update_permission(root, user, input_data, filters) for perm in perms)
        if cls._meta.model_operation == "delete":
            return all(perm.has_delete_permission(root, user, input_data, filters) for perm in perms)
        return all(perm.has_mutation_permission(root, user, input_data, filters) for perm in perms)

    @classmethod
    def mutate(cls, root: Any, info: GQLInfo, **kwargs: Any) -> Self:
        if not cls.has_permission(root=root, info=info, input_data=kwargs["input"]):
            detail = {api_settings.NON_FIELD_ERRORS_KEY: [gdx_settings.MUTATION_PERMISSION_ERROR_MESSAGE]}
            errors = ErrorType.from_errors(detail)
            return cls(errors=errors)  # type: ignore[arg-type]

        try:
            return super().mutate(root=root, info=info, input=kwargs["input"])
        except (DjangoValidationError, SerializerValidationError) as error:
            detail = as_serializer_error(error)
            detail = camelize(detail) if graphene_settings.CAMELCASE_ERRORS else detail
            detail = flatten_errors(detail)
            errors = [ErrorType(field=key, messages=value) for key, value in detail.items()]  # type: ignore[arg-type]
            return cls(errors=errors)  # type: ignore[arg-type]

    @classmethod
    def mutate_and_get_payload(cls, root: Any, info: GQLInfo, **kwargs: Any) -> Self:
        if cls._meta.model_operation == "delete":
            return cls.delete(root=root, info=info, **kwargs)
        if cls._meta.model_operation in ("create", "update"):
            return cls.update_or_delete(root=root, info=info, **kwargs)
        return cls.custom_model_operation(root=root, info=info, **kwargs)

    @classmethod
    def custom_model_operation(cls, root: Any, info: GQLInfo, **kwargs: Any) -> Self:  # pragma: no cover
        """
        Override this method to perform custom model operations in this mutation
        instead of the regular create, update or delete.
        """
        raise NotImplementedError(f"Custom model operation not defined for '{cls.__name__}'")  # noqa: EM102

    @classmethod
    def get_instance(cls, **kwargs: Any) -> models.Model:
        lookup_field: str = cls._meta.lookup_field
        if lookup_field not in kwargs:  # pragma: no cover
            raise SerializerValidationError({lookup_field: "This field is required."})
        return get_object_or_404(cls._meta.model_class, **{lookup_field: kwargs[lookup_field]})

    @classmethod
    def update_or_delete(cls, root: Any, info: GQLInfo, **kwargs: Any) -> Self:
        kwargs = cls.get_serializer_kwargs(info.context, **kwargs)
        serializer = cls._meta.serializer_class(**kwargs)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        output = cls.to_representation(obj)
        return cls(errors=None, **output)  # type: ignore[arg-type]

    @classmethod
    def get_serializer_kwargs(cls, request: HttpRequest, **kwargs: Any) -> dict[str, Any]:
        for input_dict_key, maybe_enum in kwargs.items():
            if isinstance(maybe_enum, Enum):
                kwargs[input_dict_key] = maybe_enum.value

        instance: models.Model | None = None
        if cls._meta.model_operation == "update":
            instance = cls.get_instance(**kwargs)

        return {
            "instance": instance,
            "data": kwargs,
            "context": {"request": request},
            "partial": instance is not None,
        }

    @classmethod
    def to_representation(cls, obj: models.Model) -> dict[str, Any]:
        serializer = cls._meta.output_serializer_class(instance=obj)

        kwargs: dict[str, Any] = {}
        for field_name, field in serializer.fields.items():
            if not field.write_only:
                if isinstance(field, SerializerMethodField):  # pragma: no cover
                    kwargs[field_name] = field.to_representation(obj)
                else:
                    kwargs[field_name] = field.get_attribute(obj)
        return kwargs

    @classmethod
    def delete(cls, root: Any, info: GQLInfo, **kwargs: Any) -> Self:
        instance = cls.get_instance(**kwargs)
        cls.validate_deletion(instance, info.context.user)
        count, _ = instance.delete()
        return cls(errors=None, deleted=bool(count))  # type: ignore[arg-type]

    @classmethod
    def validate_deletion(cls, instance: models.Model, user: AnyUser) -> None:
        """Implement to perform additional validation before the given instance is deleted."""
        return  # pragma: no cover


class CreateMutation(DjangoMutation):
    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(cls, **options: Any) -> None:
        super().__init_subclass_with_meta__(model_operation="create", **options)


class UpdateMutation(DjangoMutation):
    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(cls, **options: Any) -> None:
        super().__init_subclass_with_meta__(model_operation="update", **options)


class DeleteMutation(DjangoMutation):
    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(cls, **options: Any) -> None:
        super().__init_subclass_with_meta__(model_operation="delete", **options)


def _check_serializer_field_models_in_registry(
    mutation_class: type[DjangoMutation],
    serializer: ModelSerializer,
) -> None:
    global_registry = get_global_registry()

    for field in serializer.fields.values():
        if isinstance(field, ModelSerializer):
            field_model: type[models.Model] = field.Meta.model
        elif isinstance(field, ListSerializer) and isinstance(field.child, ModelSerializer):
            field = field.child  # noqa: PLW2901
            field_model: type[models.Model] = field.Meta.model
        else:
            continue

        type_ = global_registry.get_type_for_model(field_model)
        if type_ is None:  # pragma: no cover
            # This error is in place since the mutation class needs to know the ObjectTypes
            # of the models of nested model serializer fields when converting them to ObjectTypes,
            # but currently does not properly warn against this error itself. See this line in
            # `graphene_django.rest_framework.serializer_converter.convert_serializer_field`:
            #
            # args = [global_registry.get_type_for_model(field_model)]
            #
            # Since model is not registered, `global_registry.get_type_for_model` returns `None`,
            # which will cause errors later on in the mutation class creation process.
            msg = (
                f"Could not find a ObjectType for model: `{field_model.__name__}`. "
                f"Make sure that the ObjectType for this model is registered before the "
                f"`{mutation_class.__name__}` mutation class is crated. This can be archived by, "
                f"for example, setting `{field.__class__.__name__}.Meta.node` to that ObjectType."
            )
            raise LookupError(msg)

        _check_serializer_field_models_in_registry(mutation_class, field)
