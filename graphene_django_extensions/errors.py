from __future__ import annotations

import re
from typing import TYPE_CHECKING

from django.apps import apps
from django.db import models
from graphene_django.settings import graphene_settings
from graphene_django.utils import camelize
from graphql import GraphQLError
from rest_framework.serializers import as_serializer_error

from .settings import gdx_settings
from .typing import FieldError

if TYPE_CHECKING:
    from rest_framework.exceptions import ErrorDetail

    from .typing import SerializerErrorData, ValidationErrorType


__all__ = [
    "get_constraint_message",
    "GQLNotFoundError",
    "GQLPermissionDeniedError",
    "GQLValidationError",
]


class GQLPermissionDeniedError(GraphQLError):
    """Exception raised when the user has insufficient permissions to access a resource."""

    def __init__(self, message: str, code: str) -> None:
        super().__init__(message, extensions={"code": code})


class GQLNotFoundError(GraphQLError):
    """Exception raised when the user has insufficient permissions to access a resource."""

    def __init__(self, message: str, code: str) -> None:
        super().__init__(message, extensions={"code": code})


class GQLValidationError(GraphQLError):
    """Exception raised when mutation validation fails."""

    def __init__(self, error: ValidationErrorType) -> None:
        detail = as_serializer_error(error)
        if graphene_settings.CAMELCASE_ERRORS:
            detail = camelize(detail)
        detail = flatten_errors(detail)
        errors = to_field_errors(detail)
        super().__init__(
            gdx_settings.MUTATION_VALIDATION_ERROR_MESSAGE,
            extensions={"code": gdx_settings.MUTATION_VALIDATION_ERROR_CODE, "errors": errors},
        )


CONSTRAINT_PATTERNS: tuple[re.Pattern, ...] = (
    # Postgres
    re.compile(r'^new row for relation "(?P<relation>\w+)" violates check constraint "(?P<constraint>\w+)"'),
    re.compile(r'^duplicate key value violates unique constraint "(?P<constraint>\w+)"'),
    # SQLite
    re.compile(r"^CHECK constraint failed: (?P<constraint>\w+)$"),
    re.compile(r"^UNIQUE constraint failed: (?P<fields>[\w., ]+)$"),
)


def get_constraint_message(message: str) -> str:
    """Try to get the error message for a constraint violation from the model meta constraints."""
    if (match := CONSTRAINT_PATTERNS[0].match(message)) is not None:
        relation: str = match.group("relation")
        constraint: str = match.group("constraint")
        return postgres_check_constraint_message(relation, constraint, message)

    if (match := CONSTRAINT_PATTERNS[1].match(message)) is not None:
        constraint: str = match.group("constraint")
        return postgres_unique_constraint_message(constraint, message)

    if (match := CONSTRAINT_PATTERNS[2].match(message)) is not None:
        constraint: str = match.group("constraint")
        return sqlite_check_constraint_message(constraint, message)

    if (match := CONSTRAINT_PATTERNS[3].match(message)) is not None:
        fields: list[str] = match.group("fields").split(",")
        relation: str = fields[0].split(".")[0]
        fields = [field.strip().split(".")[1] for field in fields]
        return sqlite_unique_constraint_message(relation, fields, message)

    return message


def postgres_check_constraint_message(relation: str, constraint: str, default_message: str) -> str:
    for model in apps.get_models():
        if model._meta.db_table != relation:
            continue
        for constr in model._meta.constraints:
            if not isinstance(constr, models.CheckConstraint):
                continue  # pragma: no cover
            if constr.name == constraint:
                return constr.violation_error_message
    return default_message


def postgres_unique_constraint_message(constraint: str, default_message: str) -> str:
    for model in apps.get_models():
        for constr in model._meta.constraints:
            if not isinstance(constr, models.UniqueConstraint):
                continue  # pragma: no cover
            if constr.name == constraint:
                return constr.violation_error_message
    return default_message


def sqlite_check_constraint_message(constraint: str, default_message: str) -> str:
    for model in apps.get_models():
        for constr in model._meta.constraints:
            if not isinstance(constr, models.CheckConstraint):
                continue  # pragma: no cover
            if constr.name == constraint:
                return constr.violation_error_message
    return default_message


def sqlite_unique_constraint_message(relation: str, fields: list[str], default_message: str) -> str:
    for model in apps.get_models():
        if model._meta.db_table != relation:
            continue
        for constr in model._meta.constraints:
            if not isinstance(constr, models.UniqueConstraint):
                continue  # pragma: no cover
            if set(constr.fields) == set(fields):
                return constr.violation_error_message
    return default_message


def flatten_errors(errors: dict[str, list[ErrorDetail | str] | SerializerErrorData]) -> SerializerErrorData:
    """
    Flatten nested errors dict to a single level.

    >>> a = {"billing_address": {"city": ["msg1"], "post_code": ["msg2"]}}
    >>> flatten_errors(a)
    {"billing_address.city": ["msg1"], "billing_address.post_code": ["msg2"]}
    """
    flattened_errors: dict[str, list[ErrorDetail]] = {}
    for field, error in errors.items():
        if isinstance(error, dict):
            for inner_field, inner_error in flatten_errors(error).items():
                flattened_errors[f"{field}.{inner_field}"] = inner_error
        else:
            flattened_errors[field] = error

    return flattened_errors


def to_field_errors(errors: SerializerErrorData) -> list[FieldError]:
    """
    Convert a flattened errors dict to a list of field errors.

    >>> a = {
    ...     "city": [
    ...         ErrorDetail(string="msg1", code="foo"),
    ...         ErrorDetail(string="msg2", code="bar"),
    ...     ],
    ...     "post_code": ["msg3"],
    ... }
    ...
    >>> to_field_errors(a)
    [
        {"field": "city", "message": "msg1", "code": "foo"},
        {"field": "city", "message": "msg2", "code": "bar"},
        {"field": "post_code", "message": "msg3", "code": ""},
    ]
    """
    return [
        FieldError(
            field=field,
            message=message,
            code=getattr(message, "code", ""),
        )
        for field, messages in errors.items()
        for message in messages
    ]
