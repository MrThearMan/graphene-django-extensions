from __future__ import annotations

import re
from unittest.mock import Mock

import pytest
from django.contrib.auth.models import AnonymousUser, User

from graphene_django_extensions.errors import GQLFieldPermissionDeniedError
from graphene_django_extensions.permissions import (
    AllowAny,
    AllowAuthenticated,
    AllowStaff,
    AllowSuperuser,
    BasePermission,
    restricted_field,
)


def resolve_value(root, info):
    return "value"


def make_info(user: User | AnonymousUser) -> Mock:
    info = Mock()
    info.context.user = user
    return info


@pytest.mark.parametrize(
    ("permission", "user", "expected"),
    [
        (BasePermission, User(is_staff=True, is_superuser=True), False),
        (AllowAny, AnonymousUser(), True),
        (AllowAuthenticated, AnonymousUser(), False),
        (AllowAuthenticated, User(), True),
        (AllowStaff, User(is_staff=False), False),
        (AllowStaff, User(is_staff=True), True),
        (AllowSuperuser, User(is_superuser=False), False),
        (AllowSuperuser, User(is_superuser=True), True),
    ],
)
def test_permission_classes(permission, user, expected):
    assert permission.has_permission(user) is expected
    assert permission.has_filter_permission(user, filters={}) is expected
    assert permission.has_node_permission(instance=Mock(), user=user, filters={}) is expected
    assert permission.has_create_permission(user, input_data={}) is expected
    assert permission.has_update_permission(instance=Mock(), user=user, input_data={}) is expected
    assert permission.has_delete_permission(instance=Mock(), user=user, input_data={}) is expected


def test_restricted_field__check_with_user():
    resolver = restricted_field(lambda user: user.is_staff)(resolve_value)

    assert resolver(None, make_info(User(is_staff=True))) == "value"


def test_restricted_field__check_with_user_and_instance():
    root = Mock(owner="foo")
    resolver = restricted_field(lambda user, obj: obj.owner == user.username)(resolve_value)

    assert resolver(root, make_info(User(username="foo"))) == "value"


def test_restricted_field__check_returns_none():
    resolver = restricted_field(lambda _user: None)(resolve_value)

    assert resolver(None, make_info(User())) is None


def test_restricted_field__no_permission():
    resolver = restricted_field(lambda _user: False, message="No access.")(resolve_value)

    with pytest.raises(GQLFieldPermissionDeniedError, match=re.escape("No access.")):
        resolver(None, make_info(User()))
