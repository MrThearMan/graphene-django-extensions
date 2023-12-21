from __future__ import annotations

import re
from typing import TYPE_CHECKING

from django.apps import apps
from django.db import models

if TYPE_CHECKING:
    from .typing import Any


__all__ = [
    "get_constraint_message",
]


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


def flatten_errors(errors: dict[str, Any]) -> dict[str, list[str]]:
    """
    Flatten nested errors dict to a single level.

    >>> {"billing_address": {"city": ["msg1"], "post_code": ["msg2"]}}
    {"billing_address.city": ["msg1"], "billing_address.post_code": ["msg2"]}
    """
    flattened_errors: dict[str, list[str]] = {}
    for field, error in errors.items():
        if isinstance(error, dict):
            for inner_field, inner_error in flatten_errors(error).items():
                flattened_errors[f"{field}.{inner_field}"] = inner_error
        else:
            flattened_errors[field] = error

    return flattened_errors
