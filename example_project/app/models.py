from __future__ import annotations

from django.db import models

__all__ = [
    "Example",
    "ExampleState",
    "ForwardManyToMany",
    "ForwardManyToOne",
    "ForwardOneToOne",
    "ReverseManyToMany",
    "ReverseOneToMany",
    "ReverseOneToOne",
]


class ForwardOneToOne(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self) -> str:
        return self.name


class ForwardManyToOne(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self) -> str:
        return self.name


class ForwardManyToMany(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self) -> str:
        return self.name


class ExampleState(models.TextChoices):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class Example(models.Model):
    name = models.CharField(max_length=255)
    number = models.IntegerField()
    email = models.EmailField(unique=True)
    example_state = models.CharField(choices=ExampleState.choices, max_length=255)
    duration = models.DurationField()
    symmetrical_field = models.ManyToManyField("self")
    forward_one_to_one_field = models.OneToOneField(
        ForwardOneToOne,
        on_delete=models.CASCADE,
        related_name="example_rel",
    )
    forward_many_to_one_field = models.ForeignKey(
        ForwardManyToOne,
        on_delete=models.CASCADE,
        related_name="example_rels",
    )
    forward_many_to_many_fields = models.ManyToManyField(
        ForwardManyToMany,
        related_name="example_rels",
    )

    # Translation fields
    name_en: str | None
    name_fi: str | None

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "number"],
                name="unique_name",
                violation_error_message="Example unique violation message.",
            ),
            models.CheckConstraint(
                check=models.Q(name__icontains="foo"),
                name="check_example",
                violation_error_message="Example constraint violation message.",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def example_property(self) -> str:
        return "example_property"


class ReverseOneToOne(models.Model):
    name = models.CharField(max_length=255)
    example_field = models.OneToOneField(
        Example,
        on_delete=models.CASCADE,
        related_name="reverse_one_to_one_rel",
    )

    def __str__(self) -> str:
        return self.name


class ReverseOneToMany(models.Model):
    name = models.CharField(max_length=255)
    example_field = models.ForeignKey(
        Example,
        on_delete=models.CASCADE,
        related_name="reverse_one_to_many_rels",
    )

    def __str__(self) -> str:
        return self.name


class ReverseManyToMany(models.Model):
    name = models.CharField(max_length=255)
    example_fields = models.ManyToManyField(
        Example,
        related_name="reverse_many_to_many_rels",
    )

    def __str__(self) -> str:
        return self.name
