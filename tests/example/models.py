from django.db import models


class ForwardOneToOne(models.Model):
    name = models.CharField(max_length=255)


class ForwardManyToOne(models.Model):
    name = models.CharField(max_length=255)


class ForwardManyToMany(models.Model):
    name = models.CharField(max_length=255)


class State(models.TextChoices):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class Example(models.Model):
    name = models.CharField(max_length=255)
    number = models.IntegerField()
    email = models.EmailField(unique=True)
    state = models.CharField(choices=State.choices, max_length=255)
    symmetrical_field = models.ManyToManyField("self")
    forward_one_to_one_field = models.OneToOneField(
        ForwardOneToOne,
        on_delete=models.CASCADE,
        related_name="example_rel",
        related_query_name="example_query_rel",
    )
    forward_many_to_one_field = models.ForeignKey(
        ForwardManyToOne,
        on_delete=models.CASCADE,
        related_name="example_rels",
        related_query_name="example_query_rels",
    )
    forward_many_to_many_fields = models.ManyToManyField(
        ForwardManyToMany,
        related_name="example_rels",
        related_query_name="example_query_rels",
    )

    @property
    def example_property(self) -> str:
        return "example_property"

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


class ReverseOneToOne(models.Model):
    name = models.CharField(max_length=255)
    example_field = models.OneToOneField(
        Example,
        on_delete=models.CASCADE,
        related_name="reverse_one_to_one_rel",
        # See: https://github.com/graphql-python/graphene-django/issues/1484
        # related_query_name="reverse_one_to_one_query_rel",
    )


class ReverseOneToMany(models.Model):
    name = models.CharField(max_length=255)
    example_field = models.ForeignKey(
        Example,
        on_delete=models.CASCADE,
        related_name="reverse_one_to_many_rels",
        related_query_name="reverse_one_to_many_query_rels",
    )


class ReverseManyToMany(models.Model):
    name = models.CharField(max_length=255)
    example_fields = models.ManyToManyField(
        Example,
        related_name="reverse_many_to_many_rels",
        related_query_name="reverse_many_to_many_query_rels",
    )
