from __future__ import annotations

import datetime
import re
from copy import deepcopy
from dataclasses import dataclass
from functools import wraps
from typing import TYPE_CHECKING, Literal, Sequence

import graphene
from django.apps import apps
from django.db import IntegrityError, models, transaction
from graphene_django.converter import convert_django_field
from graphene_django.registry import get_global_registry
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.serializers import ListSerializer, ModelSerializer

from .typing import Any, Callable, FieldName, ParamSpec, SerializerMeta, TypedDict, TypeVar

if TYPE_CHECKING:
    from django.db.models import ForeignObjectRel
    from django.db.models.fields.related import RelatedField
    from graphene.types.unmountedtype import UnmountedType

    from .bases import DjangoMutation
    from .serializers import BaseModelSerializer
    from .typing import PermCheck, RelationType


__all__ = [
    "flatten_errors",
    "restricted_field",
    "get_rel_field_info",
]


T = TypeVar("T")
P = ParamSpec("P")


def get_nested(obj: dict | list | None, /, *args: str | int, default: Any = None) -> Any:
    """
    Get value from a nested structure containing dicts with string keys or lists,
    where the keys and list indices might not exist.

    1) `data["foo"][0]["bar"]["baz"]`
     - Might raise a `KeyError` or `IndexError` if any of the keys or indices don't exist.

    2) `get_nested(data, "foo", 0, "bar", "baz")`
     - Will return `None` (default) if any of the keys or indices don't exist.
    """
    if not args:
        return obj if obj is not None else default

    arg, args = args[0], args[1:]

    if isinstance(arg, int):
        obj = obj or []
        try:
            obj = obj[arg]
        except IndexError:
            obj = None
        return get_nested(obj, *args, default=default)

    obj = obj or {}
    return get_nested(obj.get(arg), *args, default=default)


def flatten_errors(errors: dict[str, Any]) -> dict[str, list[str]]:
    """
    Flatten nested errors dict to a single level. E.g.

    {"billing_address": {"city": ["msg1"], "post_code": ["msg2"]}}
    -> {"billing_address.city": ["msg"], "billing_address.post_code": ["msg2"]}
    """
    flattened_errors: dict[str, list[str]] = {}
    for field, error in errors.items():
        if isinstance(error, dict):
            for inner_field, inner_error in flatten_errors(error).items():
                flattened_errors[f"{field}.{inner_field}"] = inner_error
        else:
            flattened_errors[field] = error

    return flattened_errors


def restricted_field(check: PermCheck, *, message: str = "") -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator for DjangoObjectType field resolvers, which will return
    a PermissionError if the request user does not have
    appropriate permissions based on the given check.
    """
    message = message or "You do not have permission to access this field."

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                if check(args[1].context.user, args[0]):
                    return func(*args, **kwargs)
            except TypeError:
                if check(args[1].context.user):
                    return func(*args, **kwargs)

            return PermissionError(message)

        return wrapper

    return decorator


def is_valid_fields(fields: Sequence[FieldName] | Literal["__all__"]) -> bool:
    if fields == "__all__":
        return True
    return isinstance(fields, Sequence)


def get_object_or_404(model_class: type[models.Model], **kwargs: Any) -> models.Model:
    try:
        return model_class._default_manager.get(**kwargs)
    except model_class.DoesNotExist as error:
        msg = "Object does not exist."
        raise NotFound(msg) from error


def get_model_lookup_field(model_class: type[models.Model], lookup_field: str | None = None) -> str:
    if lookup_field is None:
        # Use model primary key as lookup field.
        # This is usually the 'id' field, in which case we use 'pk' instead
        # to avoid collision with the 'id' field in GraphQL Relay nodes.
        lookup_field = model_class._meta.pk.name
        if lookup_field == "id":
            lookup_field = "pk"
    return lookup_field


@dataclass
class RelatedFieldInfo:
    """Information about a related field on a model."""

    name: str
    forward: bool
    relation: RelationType

    @property
    def one_to_one(self) -> bool:
        return self.relation == "one_to_one"

    @property
    def many_to_one(self) -> bool:
        return self.relation == "many_to_one"

    @property
    def one_to_many(self) -> bool:
        return self.relation == "one_to_many"

    @property
    def many_to_many(self) -> bool:
        return self.relation == "many_to_many"

    @property
    def reverse(self) -> bool:
        return not self.forward


def get_rel_field_info(model: type[models.Model]) -> dict[str, RelatedFieldInfo]:
    """Map of all related fields on the given model to their related entity's field names."""
    mapping: dict[str, RelatedFieldInfo] = {}
    for field in model._meta.get_fields():
        if isinstance(field, (models.OneToOneRel, models.ManyToOneRel, models.ManyToManyRel)):
            name: str = field.get_accessor_name() or field.name
            mapping[name] = RelatedFieldInfo(
                name=field.remote_field.name,
                forward=False,
                relation=_get_relation_type(field),
            )

        if isinstance(field, (models.OneToOneField, models.ForeignKey, models.ManyToManyField)):
            value = field.remote_field.get_accessor_name() or field.name
            mapping[field.name] = RelatedFieldInfo(
                name=value,
                forward=True,
                relation=_get_relation_type(field),
            )
            continue

    return mapping


def _get_relation_type(field: ForeignObjectRel | RelatedField) -> RelationType:
    return (
        "one_to_one"
        if field.one_to_one
        else "many_to_one"
        if field.many_to_one
        else "one_to_many"
        if field.one_to_many
        else "many_to_many"
    )


CONSTRAINT_PATTERNS: tuple[re.Pattern, ...] = (
    # Postgres
    re.compile(r'^new row for relation "(?P<relation>\w+)" violates (check|unique) constraint "(?P<constraint>\w+)"'),
    # SQLite
    re.compile(r"^CHECK constraint failed: (?P<constraint>\w+)$"),
    re.compile(r"^UNIQUE constraint failed: (?P<fields>[\w., ]+)$"),
)


def get_constraint_message(message: str) -> str:
    """Try to get the error message for a constraint violation from the model meta constraints."""
    if (match := CONSTRAINT_PATTERNS[0].match(message)) is not None:
        relation: str = match.group("relation")
        constraint: str = match.group("constraint")
        return postgres_constraint_message(relation, constraint, message)

    if (match := CONSTRAINT_PATTERNS[1].match(message)) is not None:
        constraint: str = match.group("constraint")
        return sqlite_check_constraint_message(constraint, message)

    if (match := CONSTRAINT_PATTERNS[2].match(message)) is not None:
        fields: list[str] = match.group("fields").split(",")
        relation: str = fields[0].split(".")[0]
        fields = [field.strip().split(".")[1] for field in fields]
        return sqlite_unique_constraint_message(relation, fields, message)

    return message


def postgres_constraint_message(relation: str, constraint: str, default_message: str) -> str:
    for model in apps.get_models():
        if model._meta.db_table != relation:
            continue
        for constr in model._meta.constraints:
            if constr.name == constraint:
                return constr.violation_error_message
    return default_message


def sqlite_check_constraint_message(constraint: str, default_message: str) -> str:
    for model in apps.get_models():
        for constr in model._meta.constraints:
            if not isinstance(constr, models.CheckConstraint):
                continue
            if constr.name == constraint:
                return constr.violation_error_message
    return default_message


def sqlite_unique_constraint_message(relation: str, fields: list[str], default_message: str) -> str:
    for model in apps.get_models():
        if model._meta.db_table != relation:
            continue
        for constr in model._meta.constraints:
            if not isinstance(constr, models.UniqueConstraint):
                continue
            if set(constr.fields) == set(fields):
                return constr.violation_error_message
    return default_message


def handle_related(func: Callable[P, T]) -> Callable[P, T]:
    """Handle related models before and after creating or updating the main model."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> models.Model:
        self: BaseModelSerializer = args[0]
        validated_data = next((arg for arg in args if isinstance(arg, dict)), kwargs.get("validated_data"))
        if validated_data is None:
            msg = "'validated_data' not found in args or kwargs"
            raise ValueError(msg)

        try:
            with transaction.atomic():
                related_serializers = self._prepare_related(validated_data)
                instance = func(*args, **kwargs)
                if related_serializers:
                    self._handle_related(instance, related_serializers)
        except IntegrityError as error:
            msg = get_constraint_message(error.args[0])
            raise ValidationError(msg) from error

        return instance

    return wrapper


_CONVERSION_TABLE: dict[type, type[models.Field]] = {
    int: models.IntegerField,
    str: models.CharField,
    bool: models.BooleanField,
    float: models.FloatField,
    dict: models.JSONField,
    list: models.JSONField,
    set: models.JSONField,
    tuple: models.JSONField,
    bytes: models.BinaryField,
    datetime.time: models.TimeField,
}


def convert_typed_dict_to_graphene_type(typed_dict: type[TypedDict]) -> type[graphene.ObjectType]:
    graphene_types: dict[str, UnmountedType] = {}
    for field_name, type_ in typed_dict.__annotations__.items():
        model_field = _CONVERSION_TABLE.get(type_)
        if model_field is None:
            msg = f"Cannot convert field {field_name} of type {type_} to model field."
            raise ValueError(msg)
        graphene_type = convert_django_field(model_field())
        graphene_types[field_name] = graphene_type

    return type(f"{typed_dict.__name__}Type", (graphene.ObjectType,), graphene_types)  # type: ignore[return-value]


def convert_serializer_fields_to_not_required(
    serializer: ModelSerializer,
    lookup_field: FieldName | None,
    *,
    top_level: bool = True,
) -> type[ModelSerializer | ListSerializer]:
    """
    When updating, usually the wanted behaviour is that the user can only update the
    fields that are actually updated. Therefore, this function can be used to create a new
    serializer, on which has all the appropriate fields set to `required=False` (except
    the top-level `lookup_field`, which is required to select the row to be updated).
    This function is recursive, so that nested serializers, and their fields are also converted
    to `required=False`.

    :param serializer: The serializer to convert.
    :param lookup_field: The lookup field to be used for the update operation.
    :param top_level: Whether this is the top-level serializer.
    """
    # We need to create a new serializer and rename it since
    # `graphene_django.rest_framework.serializer_converter.convert_serializer_to_input_type`.
    # caches its results by the serializer class name, and thus the input type created for
    # the CREATE operation would be used if created first.
    class_name = f"Update{serializer.__class__.__name__}"
    new_class: type[ModelSerializer] = type(class_name, (serializer.__class__,), {})  # type: ignore[assignment]

    # Create a new Meta and deepcopy `extra_kwargs` to avoid changing the original serializer,
    # which might be used for other operations.
    new_class.Meta: SerializerMeta = type("Meta", (serializer.Meta,), {})  # type: ignore[assignment]
    new_class.Meta.extra_kwargs = deepcopy(getattr(serializer.Meta, "extra_kwargs", {}))

    lookup_field = get_model_lookup_field(new_class.Meta.model, lookup_field)

    for field_name in new_class.Meta.fields:
        # If the field is for a model property, it's `read_only=True`,
        # and should NOT be marked as `required=True`
        # (see `rest_framework.fields.Field.__init__`)
        # Lookup fields they have special handling.
        attr = getattr(new_class.Meta.model, field_name, None)
        if isinstance(attr, property) and field_name != lookup_field:
            continue

        _set_not_required(field_name, new_class.Meta, lookup_field, top_level=top_level)

    # Handle nested serializers
    for field_name, field in new_class._declared_fields.items():
        if isinstance(field, ModelSerializer):
            new_field = convert_serializer_fields_to_not_required(field, None, top_level=False)
            new_kwargs = field._kwargs | {"required": False}
            new_class._declared_fields[field_name] = new_field(*field._args, **new_kwargs)

        elif isinstance(field, ListSerializer) and isinstance(field.child, ModelSerializer):
            new_child = convert_serializer_fields_to_not_required(field.child, None, top_level=False)
            new_kwargs = field.child._kwargs | {"required": False, "many": True}
            new_class._declared_fields[field_name] = new_child(*field.child._args, **new_kwargs)

    return new_class


def _set_not_required(
    field_name: FieldName,
    meta: SerializerMeta,
    lookup_field: FieldName,
    *,
    top_level: bool,
) -> None:
    """
    Set the `required` property for `field` in the given `meta`.
    If the field is the lookup field on the top-level serializer, it should be required.
    If the field required state has been explicitly set in the serializer's `Meta.extra_kwargs`,
    it should be left as is. Otherwise, the field should not be required.
    """
    required = top_level and field_name == lookup_field

    field_options = meta.extra_kwargs.setdefault(field_name, {})
    if "required" not in field_options:
        field_options["required"] = required

    # Lookup field should be additionally marked as writeable so that
    # serializer doesn't remove it during validation.
    if field_name == lookup_field:
        meta.extra_kwargs.setdefault(field_name, {})["read_only"] = False


def check_serializer_field_models_in_registry(
    mutation_class: type[DjangoMutation],
    serializer: ModelSerializer,
) -> None:
    global_registry = get_global_registry()

    for field in serializer.fields.values():
        if isinstance(field, ModelSerializer):
            field_model: type[models.Model] = field.Meta.model
        elif isinstance(field, ListSerializer) and isinstance(field.child, ModelSerializer):
            field_model: type[models.Model] = field.child.Meta.model
        else:
            continue

        type_ = global_registry.get_type_for_model(field_model)
        if type_ is None:
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

        check_serializer_field_models_in_registry(mutation_class, field)
