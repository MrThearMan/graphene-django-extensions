from typing import TYPE_CHECKING

from .typing import Any, GQLInfo

if TYPE_CHECKING:
    from django.db.models import Model


__all__ = [
    "BasePermission",
    "AllowAny",
    "AllowAuthenticated",
    "AllowStaff",
    "AllowSuperuser",
]


class BasePermission:
    @classmethod
    def has_permission(cls, info: GQLInfo) -> bool:
        return False

    @classmethod
    def has_node_permission(cls, info: GQLInfo, pk: Any) -> bool:
        return cls.has_permission(info)

    @classmethod
    def has_mutation_permission(cls, obj: "Model", info: GQLInfo, input_data: dict[str, Any]) -> bool:
        return cls.has_permission(info)

    @classmethod
    def has_filter_permission(cls, info: GQLInfo) -> bool:
        return cls.has_permission(info)


class AllowAny(BasePermission):
    @classmethod
    def has_permission(cls, info: GQLInfo) -> bool:
        return True


class AllowAuthenticated(BasePermission):
    @classmethod
    def has_permission(cls, info: GQLInfo) -> bool:
        return info.context.user.is_authenticated


class AllowStaff(BasePermission):
    @classmethod
    def has_permission(cls, info: GQLInfo) -> bool:
        return info.context.user.is_staff


class AllowSuperuser(BasePermission):
    @classmethod
    def has_permission(cls, info: GQLInfo) -> bool:
        return info.context.user.is_superuser
