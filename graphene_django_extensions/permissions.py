from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING

from .errors import GQLFieldPermissionDeniedError
from .settings import gdx_settings
from .typing import ParamSpec, TypeVar

if TYPE_CHECKING:
    from django.db.models import Model
    from query_optimizer.typing import GraphQLFilterInfo

    from .typing import Any, AnyUser, Callable, PermCheck


T = TypeVar("T")
P = ParamSpec("P")


__all__ = [
    "AllowAny",
    "AllowAuthenticated",
    "AllowStaff",
    "AllowSuperuser",
    "BasePermission",
    "restricted_field",
]


class BasePermission:
    @classmethod
    def has_permission(cls, user: AnyUser) -> bool:  # pragma: no cover
        return False

    @classmethod
    def has_node_permission(cls, instance: Model, user: AnyUser, filters: GraphQLFilterInfo) -> bool:
        return cls.has_permission(user)

    @classmethod
    def has_filter_permission(cls, user: AnyUser, filters: GraphQLFilterInfo) -> bool:
        return cls.has_permission(user)

    @classmethod
    def has_mutation_permission(cls, user: AnyUser, input_data: dict[str, Any]) -> bool:
        return cls.has_permission(user)

    @classmethod
    def has_create_permission(cls, user: AnyUser, input_data: dict[str, Any]) -> bool:
        return cls.has_mutation_permission(user, input_data)

    @classmethod
    def has_update_permission(cls, instance: Model, user: AnyUser, input_data: dict[str, Any]) -> bool:
        return cls.has_mutation_permission(user, input_data)

    @classmethod
    def has_delete_permission(cls, instance: Model, user: AnyUser, input_data: dict[str, Any]) -> bool:
        return cls.has_mutation_permission(user, input_data)


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
    Decorator for GraphQL field resolvers, which will check if the request user has
    appropriate permissions to access the field based on the given check.

    :param check: A callable which takes the request user, and optionally
                  the ObjectType's Model instance, as its arguments, and returns
                  a boolean indicating whether the user has permission to access the field.
                  If None is returned from this, the resolver will also return None.
    :param message: The message to raise in the PermissionError.
                    If not given, use default message from settings.
    """
    message = message or gdx_settings.FIELD_PERMISSION_ERROR_MESSAGE

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                result = check(args[1].context.user, args[0])
            except TypeError:
                result = check(args[1].context.user)

            if result is None:  # pragma: no cover
                return None
            if result:  # pragma: no cover
                return func(*args, **kwargs)
            raise GQLFieldPermissionDeniedError(message=message)

        return wrapper

    return decorator
