from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING

from .settings import gdx_settings
from .typing import ParamSpec, TypeVar

if TYPE_CHECKING:
    from django.db.models import Model

    from .typing import Any, AnyUser, Callable, PermCheck


T = TypeVar("T")
P = ParamSpec("P")


__all__ = [
    "BasePermission",
    "AllowAny",
    "AllowAuthenticated",
    "AllowStaff",
    "AllowSuperuser",
    "restricted_field",
]


class BasePermission:
    @classmethod
    def has_permission(cls, user: AnyUser) -> bool:  # pragma: no cover
        return False

    @classmethod
    def has_node_permission(cls, user: AnyUser, pk: Any, filters: dict[str, Any]) -> bool:
        return cls.has_permission(user)

    @classmethod
    def has_filter_permission(cls, user: AnyUser, filters: dict[str, Any]) -> bool:
        return cls.has_permission(user)

    @classmethod
    def has_mutation_permission(
        cls,
        obj: Model,
        user: AnyUser,
        input_data: dict[str, Any],
        filters: dict[str, Any],
    ) -> bool:
        return cls.has_permission(user)

    @classmethod
    def has_create_permission(
        cls,
        obj: Model,
        user: AnyUser,
        input_data: dict[str, Any],
        filters: dict[str, Any],
    ) -> bool:
        return cls.has_mutation_permission(obj, user, input_data, filters)

    @classmethod
    def has_update_permission(
        cls,
        obj: Model,
        user: AnyUser,
        input_data: dict[str, Any],
        filters: dict[str, Any],
    ) -> bool:
        return cls.has_mutation_permission(obj, user, input_data, filters)

    @classmethod
    def has_delete_permission(
        cls,
        obj: Model,
        user: AnyUser,
        input_data: dict[str, Any],
        filters: dict[str, Any],
    ) -> bool:
        return cls.has_mutation_permission(obj, user, input_data, filters)


class AllowAny(BasePermission):
    @classmethod
    def has_permission(cls, user: AnyUser) -> bool:
        return True


class AllowAuthenticated(BasePermission):
    @classmethod
    def has_permission(cls, user: AnyUser) -> bool:  # pragma: no cover
        return user.is_authenticated


class AllowStaff(BasePermission):
    @classmethod
    def has_permission(cls, user: AnyUser) -> bool:  # pragma: no cover
        return user.is_staff


class AllowSuperuser(BasePermission):
    @classmethod
    def has_permission(cls, user: AnyUser) -> bool:  # pragma: no cover
        return user.is_superuser


def restricted_field(check: PermCheck, *, message: str = "") -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator for GraphQL field resolvers, which will return
    a PermissionError if the request user does not have
    appropriate permissions based on the given check.

    :param check: A callable, which takes the request user, and the ObjectType's Model instance
                  (or just the request user) as its arguments.
    :param message: The message to return in the PermissionError.
                    If not given, use default message from settings.
    """
    message = message or gdx_settings.PERMISSION_DENIED_MESSAGE

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                if check(args[1].context.user, args[0]):
                    return func(*args, **kwargs)  # pragma: no cover
            except TypeError:
                if check(args[1].context.user):
                    return func(*args, **kwargs)  # pragma: no cover

            return PermissionError(message)

        return wrapper

    return decorator
