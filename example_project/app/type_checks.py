"""
Static type checks for the public typing of the library.

mypy checks this module. The classes are defined only for type checking,
so they are not registered to the graphene registry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, assert_type

if TYPE_CHECKING:
    from typing import Any, TypedDict

    from django.contrib.auth.models import User
    from django.db.models import QuerySet
    from query_optimizer.typing import GQLInfo

    from example_project.app.models import Example, ExampleQuerySet, ExampleState
    from graphene_django_extensions import DjangoNode, NestingModelSerializer
    from graphene_django_extensions.fields import EnumFriendlyChoiceField
    from graphene_django_extensions.utils import get_nested

    class ExampleNodeWithQuerySet(DjangoNode[Example, User, ExampleQuerySet]):
        @classmethod
        def filter_queryset(cls, queryset: ExampleQuerySet, info: GQLInfo[User]) -> ExampleQuerySet:
            return queryset.active()

        @classmethod
        def get_queryset(cls, queryset: ExampleQuerySet, info: GQLInfo[User]) -> ExampleQuerySet:
            return queryset.active()

    class ExampleNodeWithDefaultQuerySet(DjangoNode[Example, User]):
        @classmethod
        def filter_queryset(cls, queryset: QuerySet[Example], info: GQLInfo[User]) -> QuerySet[Example]:
            return queryset.filter(example_state=ExampleState.ACTIVE)

    class ExampleData(TypedDict, total=False):
        name: str
        tags: list[dict[str, Any]]

    class ExampleSerializerWithoutInstance(NestingModelSerializer[Example, ExampleData]):
        state = EnumFriendlyChoiceField(choices=[ExampleState.ACTIVE], enum=ExampleState)

        def validate(self, attrs: ExampleData) -> ExampleData:
            # The DRF serializers allow a missing instance, e.g. when creating a new one.
            assert_type(self.instance, Example | None)
            self.get_or_default("name", attrs)
            return attrs

    def check_typed_dict_in_get_nested(data: ExampleData) -> None:
        get_nested(data, "tags", 0, "name")

    def check_default_queryset(queryset: QuerySet[Example], info: GQLInfo[User]) -> None:
        assert_type(DjangoNode[Example, User].filter_queryset(queryset, info), QuerySet[Example])

    def check_custom_queryset(queryset: ExampleQuerySet, info: GQLInfo[User]) -> None:
        object_type = DjangoNode[Example, User, ExampleQuerySet]
        assert_type(object_type.filter_queryset(queryset, info), ExampleQuerySet)
        assert_type(object_type.get_queryset(queryset, info), ExampleQuerySet)
