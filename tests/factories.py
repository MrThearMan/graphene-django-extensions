from typing import Any, Iterable

import factory
from factory import fuzzy
from factory.django import DjangoModelFactory

from tests.example.models import (
    Example,
    ForwardManyToMany,
    ForwardManyToOne,
    ForwardOneToOne,
    ReverseManyToMany,
    ReverseOneToMany,
    ReverseOneToOne,
)


class ForwardOneToOneFactory(DjangoModelFactory):
    name = fuzzy.FuzzyText()

    class Meta:
        model = ForwardOneToOne

    @classmethod
    def create(cls, **kwargs: Any) -> ForwardOneToOne:
        return super().create(**kwargs)


class ForwardManyToManyFactory(DjangoModelFactory):
    name = fuzzy.FuzzyText()

    class Meta:
        model = ForwardManyToMany

    @classmethod
    def create(cls, **kwargs: Any) -> ForwardManyToMany:
        return super().create(**kwargs)


class ForwardManyToOneFactory(DjangoModelFactory):
    name = fuzzy.FuzzyText()

    class Meta:
        model = ForwardManyToOne

    @classmethod
    def create(cls, **kwargs: Any) -> ForwardManyToOne:
        return super().create(**kwargs)


class ExampleFactory(DjangoModelFactory):
    name = fuzzy.FuzzyText(suffix="foo")
    number = fuzzy.FuzzyInteger(0)
    email = factory.LazyAttribute(lambda example: f"{example.name}@email.com")
    forward_one_to_one_field = factory.SubFactory(ForwardOneToOneFactory)
    forward_many_to_one_field = factory.SubFactory(ForwardManyToOneFactory)

    class Meta:
        model = Example

    @classmethod
    def create(cls, **kwargs: Any) -> Example:
        return super().create(**kwargs)

    @factory.post_generation
    def forward_many_to_many_fields(
        obj: Example,
        create: bool,
        objs: Iterable[ForwardManyToMany] | None,
        **kwargs: Any,
    ) -> None:
        if not create:
            return

        if not objs and kwargs:
            obj.forward_many_to_many_fields.add(ForwardManyToManyFactory.create(**kwargs))

        for group in objs or []:
            obj.forward_many_to_many_fields.add(group)

    @factory.post_generation
    def symmetrical(obj: Example, create: bool, objs: Iterable[Example] | None, **kwargs: Any) -> None:
        if not create:
            return

        if not objs and kwargs:
            obj.symmetrical.add(ExampleFactory.create(**kwargs))

        for group in objs or []:
            obj.symmetrical.add(group)


class ReverseOneToOneFactory(DjangoModelFactory):
    name = fuzzy.FuzzyText()
    example_field = factory.SubFactory(ExampleFactory)

    class Meta:
        model = ReverseOneToOne

    @classmethod
    def create(cls, **kwargs: Any) -> ReverseOneToOne:
        return super().create(**kwargs)


class ReverseManyToManyFactory(DjangoModelFactory):
    name = fuzzy.FuzzyText()

    class Meta:
        model = ReverseManyToMany

    @classmethod
    def create(cls, **kwargs: Any) -> ReverseManyToMany:
        return super().create(**kwargs)

    @factory.post_generation
    def example_fields(obj: ReverseManyToMany, create: bool, objs: Iterable[Example] | None, **kwargs: Any) -> None:
        if not create:
            return

        if not objs and kwargs:
            obj.example_fields.add(ExampleFactory.create(**kwargs))

        for group in objs or []:
            obj.example_fields.add(group)


class ReverseOneToManyFactory(DjangoModelFactory):
    name = fuzzy.FuzzyText()
    example_field = factory.SubFactory(ExampleFactory)

    class Meta:
        model = ReverseOneToMany

    @classmethod
    def create(cls, **kwargs: Any) -> ReverseOneToMany:
        return super().create(**kwargs)
