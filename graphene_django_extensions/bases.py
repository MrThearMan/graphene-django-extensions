from __future__ import annotations

from enum import Enum
from functools import partial
from typing import TYPE_CHECKING

import graphene
from django.core.exceptions import ValidationError as DjangoValidationError
from django.forms import Form, ModelForm
from graphene import ClientIDMutation, Field, InputField
from graphene.types.resolver import attr_resolver
from graphene.types.utils import yank_fields_from_attrs
from graphene_django import DjangoObjectType
from graphene_django.converter import convert_django_field
from graphene_django.forms.mutation import fields_for_form
from graphene_django.registry import get_global_registry
from graphene_django.rest_framework.mutation import fields_for_serializer
from graphene_django.types import ALL_FIELDS
from graphene_django.utils import is_valid_django_model
from graphql_relay import to_global_id
from query_optimizer import DjangoConnectionField, DjangoListField, optimize_single
from query_optimizer.settings import optimizer_settings
from rest_framework.exceptions import ValidationError as SerializerValidationError
from rest_framework.fields import SerializerMethodField, get_attribute
from rest_framework.serializers import ListSerializer, ModelSerializer, Serializer

from .connections import Connection
from .converters import convert_form_fields_to_not_required, convert_serializer_fields_to_not_required
from .errors import GQLPermissionDeniedError, GQLValidationError
from .fields import RelatedField
from .model_operations import get_model_lookup_field, get_object_or_404
from .options import DjangoMutationOptions, DjangoNodeOptions
from .permissions import AllowAny, BasePermission, restricted_field
from .settings import gdx_settings
from .typing import Fields, Sequence
from .utils import add_translatable_fields, get_filter_info

if TYPE_CHECKING:
    from django.db import models
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

    @classmethod
    def Field(cls, **kwargs: Any) -> Field:  # noqa: N802
        return Field(cls, **kwargs)

    @classmethod
    def RelatedField(cls, **kwargs: Any) -> RelatedField:  # noqa: N802
        return RelatedField(cls, **kwargs)

    @classmethod
    def ListField(cls, **kwargs: Any) -> DjangoListField:  # noqa: N802
        return DjangoListField(cls, **kwargs)

    @classmethod
    def Node(cls, **kwargs: Any) -> NodeField:  # noqa: N802
        return graphene.relay.Node.Field(cls, **kwargs)

    @classmethod
    def Connection(cls, **kwargs: Any) -> DjangoConnectionField:  # noqa: N802
        return DjangoConnectionField(cls, **kwargs)  # pragma: no cover

    @classmethod
    def filter_queryset(cls, queryset: models.QuerySet, info: GQLInfo) -> models.QuerySet:
        """Implement this method filter to the available rows from the model on this node."""
        return queryset

    @classmethod
    def __init_subclass_with_meta__(  # noqa: PLR0913
        cls,
        model: type[models.Model] | None = None,
        fields: Fields | None = None,
        permission_classes: Sequence[type[BasePermission]] = (AllowAny,),
        restricted_fields: dict[FieldNameStr, PermCheck] | None = None,
        max_complexity: int | None = None,
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

        if fields != ALL_FIELDS:
            fields = add_translatable_fields(model, fields)

        if not hasattr(cls, "pk") and (fields == ALL_FIELDS or "pk" in fields):
            cls._add_pk_field(model)

        if restricted_fields is not None:
            cls._add_field_restrictions(fields, restricted_fields)

        _meta = DjangoNodeOptions(
            class_type=cls,
            max_complexity=max_complexity or optimizer_settings.MAX_COMPLEXITY,
            permission_classes=permission_classes,
        )
        options.setdefault("connection_class", Connection)
        options.setdefault("interfaces", (graphene.relay.Node,))

        filterset_class = options.get("filterset_class", None)
        filter_fields: dict[str, list[str]] | None = options.pop("filter_fields", None)

        if filterset_class is None and filter_fields is not None:  # pragma: no cover
            from query_optimizer.filter import create_filterset

            options["filterset_class"] = create_filterset(model, filter_fields)

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
            raise GQLPermissionDeniedError(
                message=gdx_settings.FILTER_PERMISSION_ERROR_MESSAGE,
                code=gdx_settings.FILTER_PERMISSION_ERROR_CODE,
            )
        return queryset

    @classmethod
    def get_node(cls, info: GQLInfo, pk: Any) -> models.Model | None:
        """Override `filter_queryset` instead of this method to add filtering of possible rows."""
        queryset = cls._meta.model._default_manager.all()
        instance = optimize_single(queryset, info, pk=pk, max_complexity=cls._meta.max_complexity)
        if instance is not None and not cls.has_node_permissions(info, instance):
            raise GQLPermissionDeniedError(
                message=gdx_settings.QUERY_PERMISSION_ERROR_MESSAGE,
                code=gdx_settings.QUERY_PERMISSION_ERROR_CODE,
            )
        return instance

    @classmethod
    def has_node_permissions(cls, info: GQLInfo, instance: models.Model) -> bool:
        """Check which permissions are required to access single items of this type."""
        filters = get_filter_info(info)
        return all(
            perm.has_node_permission(
                instance=instance,
                user=info.context.user,
                filters=filters,
            )
            for perm in cls._meta.permission_classes
        )

    @classmethod
    def has_filter_permissions(cls, info: GQLInfo) -> bool:
        """Check which permissions are required to access lists of this type."""
        filters = get_filter_info(info)
        return all(
            perm.has_filter_permission(
                user=info.context.user,
                filters=filters,
            )
            for perm in cls._meta.permission_classes
        )

    @classmethod
    def get_global_id(cls, pk: Any) -> str:
        """Get id used for `node` queries."""
        return to_global_id(cls.__name__, pk)


class DjangoMutation(ClientIDMutation):
    """
    Custom base class for GraphQL-mutations that are backed by a Django model.
    Adds the following features to all types that inherit it:

    - For updates, converts all fields to optional fields, enabling partial updates.

    - Checks for missing object types for nested model serializer fields to avoid nebulous import order errors.

    - Can add permission checks via permission classes.

    - Converts raise serializer validation errors to GraphQL validation errors.

    ---

    The following options can be set in the `Meta`-class.

    `model: type[models.Model]`

    - Required (delete only). Model class for the model the operation is performed on.

    `serializer_class: type[ModelSerializer | Serializer]`

    - Required (create and update only). The serializer used for the mutation.
      Type should be ModelSerializer for update and create operations, and Serializer for custom ones.

    `output_serializer_class: type[ModelSerializer | Serializer]`

    - Optional. The serializer used for the output data. If not set, `serializer_class` is used.
      Type should be ModelSerializer for update and create operations, and Serializer for custom ones.
      Serializer fields are modified so that all fields are optional, enabling partial updates.

    `permission_classes: Sequence[type[BasePermission]]`

    - Optional. Set permission classes for the mutation. Defaults to (`AllowAny`,).

    `lookup_field: str`

    - Optional. The field used for looking up the instance to be mutated. Defaults to the object's
      primary key, which is usually `id`. Note that the `lookup_field` attribute has to be available
      from the serializer's `Meta.fields` definition.

    `form_class: type[ModelForm | Form]`

    - Optional. Can be used instead of `serializer_class`.
      Type should be ModelForm for update and create operations, and Form for custom ones.

    `output_form_class: type[ModelForm | Form]`

    - Optional. Can be used instead of `output_serializer_class`.
      Type should be ModelForm for update and create operations, and Form for custom ones.
    """

    _meta: DjangoMutationOptions

    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(  # noqa: PLR0913
        cls,
        lookup_field: FieldNameStr | None = None,
        model: type[models.Model] | None = None,
        serializer_class: type[ModelSerializer | Serializer] | None = None,
        output_serializer_class: type[ModelSerializer | Serializer] | None = None,
        form_class: type[ModelForm | Form] | None = None,
        output_form_class: type[ModelForm | Form] | None = None,
        permission_classes: Sequence[type[BasePermission]] = (AllowAny,),
        model_operation: Literal["create", "update", "delete", "custom"] = "custom",
        **options: Any,
    ) -> None:
        _meta = DjangoMutationOptions(
            class_type=cls,
            lookup_field=lookup_field,
            model_class=model,
            serializer_class=serializer_class,
            output_serializer_class=output_serializer_class,
            form_class=form_class,
            output_form_class=output_form_class,
            permission_classes=permission_classes,
            model_operation=model_operation,
        )

        if model_operation in ("create", "update"):
            if serializer_class is not None:
                return cls.__init_subclass_update_or_create__(
                    _meta,
                    lookup_field,
                    serializer_class,
                    output_serializer_class,
                    model_operation,  # type: ignore[arg-type]
                    **options,
                )
            if form_class is not None:
                return cls.__init_subclass_form__(
                    _meta,
                    ModelForm,
                    form_class,
                    output_form_class,
                    **options,
                )

            msg = (  # pragma: no cover
                "`Meta.serializer_class` or `Meta.form_class` is required for create and update mutations."
            )
            raise ValueError(msg)  # pragma: no cover

        if model_operation == "delete":
            return cls.__init_subclass_delete__(
                _meta,
                lookup_field,
                model,
                **options,
            )

        if cls.custom_mutation == DjangoMutation.custom_mutation:  # pragma: no cover
            msg = "`custom_mutation` must be overridden in subclasses for custom mutations."
            raise ValueError(msg)

        if serializer_class is not None:
            return cls.__init_subclass_custom__(
                _meta,
                serializer_class,
                output_serializer_class,
                **options,
            )
        if form_class is not None:
            return cls.__init_subclass_form__(
                _meta,
                Form,
                form_class,
                output_form_class,
                **options,
            )

        msg = "`Meta.serializer_class` or `Meta.form_class` is required for custom mutations."  # pragma: no cover
        raise ValueError(msg)  # pragma: no cover

    @classmethod
    def __init_subclass_update_or_create__(
        cls,
        _meta: DjangoMutationOptions,
        lookup_field: FieldNameStr | None,
        serializer_class: type[ModelSerializer],
        output_serializer_class: type[ModelSerializer] | None,
        model_operation: Literal["create", "update"],
        **options: Any,
    ) -> None:
        if not issubclass(serializer_class, ModelSerializer):  # pragma: no cover
            msg = "`Meta.serializer_class` needs to be a ModelSerializer subclass."
            raise TypeError(msg)

        model = serializer_class.Meta.model
        lookup_field = get_model_lookup_field(model, lookup_field)

        if model_operation == "update":
            serializer_class = convert_serializer_fields_to_not_required(serializer_class, lookup_field)

        output_serializer_class = output_serializer_class or serializer_class
        if not issubclass(output_serializer_class, ModelSerializer):  # pragma: no cover
            msg = "`Meta.output_serializer_class` needs to be a ModelSerializer subclass."
            raise TypeError(msg)

        serializer = serializer_class()
        output_serializer = output_serializer_class()

        _check_serializer_field_models_in_registry(cls, output_serializer)

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

        _meta.lookup_field = lookup_field
        _meta.model_class = model
        _meta.serializer_class = serializer_class
        _meta.output_serializer_class = output_serializer_class

        return cls.__finish_init_subclass__(_meta, input_fields, output_fields, **options)

    @classmethod
    def __init_subclass_delete__(
        cls,
        _meta: DjangoMutationOptions,
        lookup_field: FieldNameStr | None,
        model: type[models.Model] | None,
        **options: Any,
    ) -> None:
        if model is None:  # pragma: no cover
            msg = "`Meta.model` is required."
            raise ValueError(msg)

        lookup_field = get_model_lookup_field(model, lookup_field)
        input_field = graphene.ID(required=True)
        if lookup_field != "pk":  # pragma: no cover
            input_field = convert_django_field(model._meta.get_field(lookup_field))

        input_fields = {lookup_field: input_field}
        output_fields = {"deleted": graphene.Boolean()}

        _meta.lookup_field = lookup_field

        return cls.__finish_init_subclass__(_meta, input_fields, output_fields, **options)

    @classmethod
    def __init_subclass_custom__(
        cls,
        _meta: DjangoMutationOptions,
        serializer_class: type[Serializer],
        output_serializer_class: type[Serializer] | None,
        **options: Any,
    ) -> None:
        if not issubclass(serializer_class, Serializer):  # pragma: no cover
            msg = "`Meta.serializer_class` needs to be a Serializer subclass."
            raise TypeError(msg)

        output_serializer_class = output_serializer_class or serializer_class
        if not issubclass(output_serializer_class, Serializer):  # pragma: no cover
            msg = "`Meta.output_serializer_class` needs to be a Serializer subclass."
            raise TypeError(msg)

        serializer = serializer_class()
        output_serializer = output_serializer_class()

        input_fields = fields_for_serializer(serializer, only_fields=(), exclude_fields=(), is_input=True)
        output_fields = fields_for_serializer(output_serializer, only_fields=(), exclude_fields=())

        _meta.serializer_class = serializer_class
        _meta.output_serializer_class = output_serializer_class

        return cls.__finish_init_subclass__(_meta, input_fields, output_fields, **options)

    @classmethod
    def __init_subclass_form__(
        cls,
        _meta: DjangoMutationOptions,
        required_form_class: type[ModelForm | Form],
        form_class: type[ModelForm, Form],
        output_form_class: type[ModelForm, Form] | None,
        **options: Any,
    ) -> None:
        if not issubclass(form_class, required_form_class):  # pragma: no cover
            msg = f"`Meta.form_class` needs to be a {required_form_class.__name__} subclass."
            raise TypeError(msg)

        output_form_class = output_form_class or form_class
        if not issubclass(output_form_class, required_form_class):  # pragma: no cover
            msg = f"`Meta.output_form_class` needs to be a {required_form_class.__name__} subclass."
            raise TypeError(msg)

        form = form_class()
        output_form_class = convert_form_fields_to_not_required(output_form_class)
        output_form = output_form_class()

        input_fields = fields_for_form(form, only_fields=(), exclude_fields=())
        output_fields = fields_for_form(output_form, only_fields=(), exclude_fields=())

        _meta.form_class = form_class
        _meta.output_form_class = output_form_class

        return cls.__finish_init_subclass__(_meta, input_fields, output_fields, **options)

    @classmethod
    def __finish_init_subclass__(
        cls,
        _meta: DjangoMutationOptions,
        input_fields: dict[str, MountedType | UnmountedType],
        output_fields: dict[str, MountedType | UnmountedType],
        **options: Any,
    ) -> None:
        input_fields = yank_fields_from_attrs(attrs=input_fields, _as=InputField)
        _meta.fields = yank_fields_from_attrs(attrs=output_fields, _as=Field)
        super().__init_subclass_with_meta__(_meta=_meta, input_fields=input_fields, **options)

    @classmethod
    def mutate(cls, root: Any, info: GQLInfo, **kwargs: Any) -> Self:
        try:
            return super().mutate(root, info, kwargs["input"])
        except (DjangoValidationError, SerializerValidationError) as error:
            raise GQLValidationError(error) from error

    @classmethod
    def mutate_and_get_payload(cls, root: Any, info: GQLInfo, **kwargs: Any) -> Self:
        if cls._meta.model_operation == "delete":
            return cls.delete(info, **kwargs)
        if cls._meta.model_operation in ("create", "update"):
            return cls.update_or_create(info, **kwargs)

        if not cls.has_mutation_permission(info, kwargs):
            raise GQLPermissionDeniedError(
                message=gdx_settings.MUTATION_PERMISSION_ERROR_MESSAGE,
                code=gdx_settings.MUTATION_PERMISSION_ERROR_CODE,
            )

        cls.run_validation(data=kwargs)
        return cls.custom_mutation(info, **kwargs)

    @classmethod
    def custom_mutation(cls, info: GQLInfo, **kwargs: Any) -> Self:  # pragma: no cover
        """Override this method to perform custom mutations instead of the regular create, update or delete."""
        raise NotImplementedError(f"Custom model operation not defined for '{cls.__name__}'")  # noqa: EM102

    @classmethod
    def get_instance(cls, **kwargs: Any) -> models.Model | None:
        if cls._meta.model_operation == "create":
            return None
        lookup_field: str = cls._meta.lookup_field
        if lookup_field not in kwargs:  # pragma: no cover
            raise SerializerValidationError({lookup_field: "This field is required."})
        return get_object_or_404(cls._meta.model_class, **{lookup_field: kwargs[lookup_field]})

    @classmethod
    def update_or_create(cls, info: GQLInfo, **kwargs: Any) -> Self:
        maybe_instance = cls.get_instance(**kwargs)

        if cls._meta.model_operation == "create" and not cls.has_create_permissions(info, kwargs):
            raise GQLPermissionDeniedError(
                message=gdx_settings.CREATE_PERMISSION_ERROR_MESSAGE,
                code=gdx_settings.CREATE_PERMISSION_ERROR_CODE,
            )
        if cls._meta.model_operation == "update" and not cls.has_update_permissions(maybe_instance, info, kwargs):
            raise GQLPermissionDeniedError(
                message=gdx_settings.UPDATE_PERMISSION_ERROR_MESSAGE,
                code=gdx_settings.UPDATE_PERMISSION_ERROR_CODE,
            )

        validator_kwargs = cls.get_validator_kwargs(maybe_instance, info, kwargs)
        validator = cls.run_validation(**validator_kwargs)
        instance = validator.save()

        if cls._meta.serializer_class is not None:
            output = cls.get_serializer_output(instance)
        else:
            output = cls.get_form_output(instance)

        return cls(**output)  # type: ignore[arg-type]

    @classmethod
    def get_validator_kwargs(cls, instance: models.Model | None, info: GQLInfo, data: dict[str, Any]) -> dict[str, Any]:
        for input_dict_key, maybe_enum in data.items():
            if isinstance(maybe_enum, Enum):
                data[input_dict_key] = maybe_enum.value

        validator_kwargs: dict[str, Any] = {"instance": instance, "data": data}
        if cls._meta.serializer_class is not None:
            validator_kwargs["context"] = {"request": info.context}
            validator_kwargs["partial"] = instance is not None

        return validator_kwargs

    @classmethod
    def run_validation(cls, **kwargs: Any) -> Serializer | Form:
        validator_class = cls._meta.serializer_class or cls._meta.form_class
        validator = validator_class(**kwargs)
        if not validator.is_valid():
            raise SerializerValidationError(validator.errors)
        return validator

    @classmethod
    def get_serializer_output(cls, instance: models.Model) -> dict[str, Any]:
        serializer = cls._meta.output_serializer_class()

        kwargs: dict[str, Any] = {}
        for field_name, field in serializer.fields.items():
            if not field.write_only:
                if isinstance(field, SerializerMethodField):  # pragma: no cover
                    kwargs[field_name] = field.to_representation(instance)
                else:
                    kwargs[field_name] = field.get_attribute(instance)
        return kwargs

    @classmethod
    def get_form_output(cls, instance: models.Model) -> dict[str, Any]:
        form = cls._meta.output_form_class()
        return {field_name: get_attribute(instance, [field_name]) for field_name in form.fields}

    @classmethod
    def delete(cls, info: GQLInfo, **kwargs: Any) -> Self:
        instance = cls.get_instance(**kwargs)
        if not cls.has_delete_permissions(instance, info, kwargs):
            raise GQLPermissionDeniedError(
                message=gdx_settings.DELETE_PERMISSION_ERROR_MESSAGE,
                code=gdx_settings.DELETE_PERMISSION_ERROR_CODE,
            )

        cls.validate_deletion(instance, info.context.user)
        count, _ = instance.delete()
        return cls(deleted=bool(count))  # type: ignore[arg-type]

    @classmethod
    def validate_deletion(cls, instance: models.Model, user: AnyUser) -> None:
        """Implement to perform additional validation before the given instance is deleted."""
        return  # pragma: no cover

    @classmethod
    def has_mutation_permission(cls, info: GQLInfo, input_data: dict[str, Any]) -> bool:
        return all(
            perm.has_mutation_permission(
                user=info.context.user,
                input_data=input_data,
            )
            for perm in cls._meta.permission_classes
        )

    @classmethod
    def has_create_permissions(cls, info: GQLInfo, input_data: dict[str, Any]) -> bool:
        return all(
            perm.has_create_permission(
                user=info.context.user,
                input_data=input_data,
            )
            for perm in cls._meta.permission_classes
        )

    @classmethod
    def has_update_permissions(cls, instance: models.Model, info: GQLInfo, input_data: dict[str, Any]) -> bool:
        return all(
            perm.has_update_permission(
                instance=instance,
                user=info.context.user,
                input_data=input_data,
            )
            for perm in cls._meta.permission_classes
        )

    @classmethod
    def has_delete_permissions(cls, instance: models.Model, info: GQLInfo, input_data: dict[str, Any]) -> bool:
        return all(
            perm.has_delete_permission(
                instance=instance,
                user=info.context.user,
                input_data=input_data,
            )
            for perm in cls._meta.permission_classes
        )


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
