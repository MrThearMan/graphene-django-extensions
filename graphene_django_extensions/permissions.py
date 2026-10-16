from __future__ import annotations

from functools import wraps
from inspect import signature
from typing import TYPE_CHECKING, Generic

from .errors import GQLFieldPermissionDeniedError
from .settings import gdx_settings
from .typing import TModel, TUser

if TYPE_CHECKING:
    from django.db.models import Model
    from query_optimizer.typing import GraphQLFilterInfo

    from .typing import Any, AnyUser, Callable, PermCheck


__all__ = [
    "AllowAny",
    "AllowAuthenticated",
    "AllowStaff",
    "AllowSuperuser",
    "BasePermission",
    "restricted_field",
]


# Type parameter defaults need Python 3.13 in the PEP 695 syntax.
class BasePermission(Generic[TModel, TUser]):  # noqa: UP046
    """
    Base class for permission classes.

    Subscribe with the model and the user type, e.g. `BasePermission[Example, User]`,
    to type the hooks for them. Without subscription, the defaults apply.
    """

    @classmethod
    def has_permission(cls, user: TUser) -> bool:
        return False

    @classmethod
    def has_node_permission(cls, instance: TModel, user: TUser, filters: GraphQLFilterInfo) -> bool:
        return cls.has_permission(user)

    @classmethod
    def has_filter_permission(cls, user: TUser, filters: GraphQLFilterInfo) -> bool:
        return cls.has_permission(user)

    @classmethod
    def has_mutation_permission(cls, user: TUser, input_data: dict[str, Any]) -> bool:
        return cls.has_permission(user)

    @classmethod
    def has_create_permission(cls, user: TUser, input_data: dict[str, Any]) -> bool:
        return cls.has_mutation_permission(user, input_data)

    @classmethod
    def has_update_permission(cls, instance: TModel, user: TUser, input_data: dict[str, Any]) -> bool:
        return cls.has_mutation_permission(user, input_data)

    @classmethod
    def has_delete_permission(cls, instance: TModel, user: TUser, input_data: dict[str, Any]) -> bool:
        return cls.has_mutation_permission(user, input_data)


class AllowAny(BasePermission):
    @classmethod
    def has_permission(cls, user: AnyUser) -> bool:
        return True


class AllowAuthenticated(BasePermission):
    @classmethod
    def has_permission(cls, user: AnyUser) -> bool:
        return user.is_authenticated


class AllowStaff(BasePermission):
    @classmethod
    def has_permission(cls, user: AnyUser) -> bool:
        return user.is_staff


class AllowSuperuser(BasePermission):
    @classmethod
    def has_permission(cls, user: AnyUser) -> bool:
        return user.is_superuser


def restricted_field[U, M: Model, **P, T](
    check: PermCheck[U, M],
    *,
    message: str = "",
) -> Callable[[Callable[P, T]], Callable[P, T | None]]:
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

    # The check takes either the user only, or the user and the model instance.
    perm_check: Callable[..., bool | None] = check
    takes_instance = _accepts_arguments(check, 2)

    def decorator(func: Callable[P, T]) -> Callable[P, T | None]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | None:
            # Resolver arguments are (root, info, ...).
            root: Any = args[0]
            info: Any = args[1]
            result = perm_check(info.context.user, root) if takes_instance else perm_check(info.context.user)

            if result is None:
                return None
            if result:
                return func(*args, **kwargs)
            raise GQLFieldPermissionDeniedError(message=message)

        return wrapper

    return decorator


def _accepts_arguments(func: Callable[..., Any], count: int) -> bool:
    """Check whether the given function can be called with the given number of positional arguments."""
    try:
        signature(func).bind(*range(count))
    except TypeError:
        return False
    return True
