from django.db import models

from graphene_django_extensions.filters import BaseModelFilterSet, IntMultipleChoiceFilter
from tests.example.models import Example


class ExampleFilterSet(BaseModelFilterSet):
    pk = IntMultipleChoiceFilter()

    class Meta:
        model = Example
        fields = [
            "pk",
            "name",
            "number",
            "email",
        ]
        order_by = [
            "pk",
            "name",
            "number",
            "email",
        ]

    def order_by_number(self, qs: models.QuerySet, *, desc: bool) -> models.QuerySet:
        return qs.order_by("-number" if desc else "number")
