import random

from django.core.management import call_command
from django.core.management.base import BaseCommand
from faker import Faker

from tests.example.models import (
    Example,
    ExampleState,
    ForwardManyToMany,
    ForwardManyToOne,
    ForwardOneToOne,
    ReverseManyToMany,
    ReverseOneToMany,
    ReverseOneToOne,
)

faker = Faker(locale="en_US")


class Command(BaseCommand):
    help = "Create test data."

    def handle(self, *args, **options) -> None:  # noqa: ANN002, ANN003
        create_test_data()


def create_test_data() -> None:
    call_command("flush", "--noinput")

    f10 = ForwardOneToOne.objects.create(name=faker.name())
    f11 = ForwardOneToOne.objects.create(name=faker.name())
    f20 = ForwardManyToOne.objects.create(name=faker.name())
    f21 = ForwardManyToOne.objects.create(name=faker.name())
    f30 = ForwardManyToMany.objects.create(name=faker.name())
    f31 = ForwardManyToMany.objects.create(name=faker.name())
    f32 = ForwardManyToMany.objects.create(name=faker.name())

    e1 = Example.objects.create(
        name="foo: " + faker.name(),
        number=random.randint(0, 100),
        email=faker.safe_email(),
        example_state=ExampleState.ACTIVE.value,
        forward_one_to_one_field=f10,
        forward_many_to_one_field=f20,
    )
    e1.forward_many_to_many_fields.add(f30, f31)

    e2 = Example.objects.create(
        name="foo: " + faker.name(),
        number=random.randint(0, 100),
        email=faker.safe_email(),
        example_state=ExampleState.INACTIVE.value,
        forward_one_to_one_field=f11,
        forward_many_to_one_field=f21,
    )
    e2.forward_many_to_many_fields.add(f30, f32)

    e1.symmetrical_field.add(e2)

    ReverseOneToOne.objects.create(name=faker.name(), example_field=e1)
    ReverseOneToOne.objects.create(name=faker.name(), example_field=e2)

    ReverseOneToMany.objects.create(name=faker.name(), example_field=e1)
    ReverseOneToMany.objects.create(name=faker.name(), example_field=e1)
    ReverseOneToMany.objects.create(name=faker.name(), example_field=e2)
    ReverseOneToMany.objects.create(name=faker.name(), example_field=e2)

    r30 = ReverseManyToMany.objects.create(name=faker.name())
    r30.example_fields.add(e1, e2)
    r31 = ReverseManyToMany.objects.create(name=faker.name())
    r31.example_fields.add(e1, e2)
