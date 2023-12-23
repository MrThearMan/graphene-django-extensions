# Filtering

## ModelFilterSet

A custom FilterSet class for optimizing the filtering of GraphQL queries.

```python
from graphene_django_extensions import ModelFilterSet
from example.models import Example

class ExampleFilterSet(ModelFilterSet):
    class Meta:
        model = Example
        fields = [...]
```

Extends from `django_filters.filterset.FilterSet` and adds the following features:

- Automatically a `order_by = CustomOrderingFilter(fields=["pk"])` to the class for ordering the filterset.
- Changes the default filters for all relationships (`one-to-one`, `many-to-one`, etc.) to not make a database
  queries to check if the filtered rows exists.

---

Subclasses can be configured through the `Meta`-class. Here are the most useful options:

| Option                | Type                                               | Description                                                                                                                                                                                                                     |
|-----------------------|----------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `model`               | `type[Model]`                                      | Required. The model class for the filterset.                                                                                                                                                                                    |
| `fields`              | `list[str]` or `dict[str, list[str]]` or `__all__` | Required. The fields to include in the node. If `__all__` is used, all fields are included.                                                                                                                                     |
| `order_by`            | `list[str]` or `list[tuple[str, str]]`             | Optional. Ordering filters to add to the filterset. Can also add non-field orderings, or customize field orderings by adding a `order_by_{field_name}` method to the `ModelFilterSet` subclass.                                 |
| `combination_methods` | `list[str]`                                        | Optional. Allows combining [method filters] so that they will use the same filter function. The combination method will always run, and its value will be a mapping of the field names of the combined filters to their values. |

---

## CustomOrderingFilter

Extends `django_filters.filters.OrderingFilter` by adding option for custom orderings
by defining `order_by_{name}` functions on its subclasses or filtersets it is defined on.
This filter is automatically added to `ModelFilterSet` subclasses, and its `Meta.order_by`
can be used to add custom orderings.

```python
from graphene_django_extensions import ModelFilterSet

class ExampleFilterSet(ModelFilterSet):
    class Meta:
        model = Example
        fields = [...]
        order_by = ["-name", "order_by_name"]

    def order_by_name(self, qs: QuerySet, desc: bool) -> QuerySet:
        return qs.order_by("name")
```

---

# UserDefinedFilter

A filter which allows users to define custom filtering rules for a set of predefined model fields.
The idea is similar in concept to the GraphQL itself; allowing users to select which data they actually
need vs. what has been predefined.

```python
from graphene_django_extensions.filters import ModelFilterSet, UserDefinedFilter

class ExampleFilterSet(ModelFilterSet):
    filter = UserDefinedFilter(
        model=Example,
        fields=["name", "number", "email"],
    )
```

Given the above filter, the user can define the following filter:

```graphql
query {
    examples(
        filter: {
            field: name,
            operator: CONTAINS,
            value: "foo",
        }
    ) {
        edges {
            node {
                pk
            }
        }
    }
}
```

This creates a simple `Q(name__contains="foo")` filter for the queryset.

Notice that the `field` values are enums created from the defined fields in the UserDefinedFilter.
If no fields are given, all fields from the given model can be filtered on. Related fields can also be
added via the "__" lookup syntax. Filter aliases can be given by specifying a tuple of
`("field_lookup", "alias")` in the fields list.

The model argument is mandatory, and is used to rename the filter input type after the `field` enum field
has been added to it (in additions fetching the default fields if no fields are defined).

Let's see a more complex example:

```graphql
query {
    examples(
        filter: {
            operator: AND,
            operations: [
                {
                    operator: OR,
                    operations: [
                        {
                            field: name,
                            operator: CONTAINS,
                            value: "foo",
                        },
                        {
                            field: email,
                            operator: CONTAINS,
                            value: "foo",
                        },
                    ],
                },
                {
                    operator: NOT,
                    operations: [
                        {
                            field: number,
                            operator: LT,
                            value: 10,
                        }
                    ]
                },
            ],
        }
    ) {
        edges {
            node {
                pk
            }
        }
    }
}
```

This configuration corresponds to `(Q(name__contains="foo") | Q(email__contains="foo") & ~Q(number__lt=10))`.

As the above example demonstrates, logical operations can also be used, allowing for complex
filtering rules to be defined, which regular filter fields cannot do.

---

## EnumChoiceFilter & EnumMultipleChoiceFilter

Custom fields for handling enums better in GraphQL filters.
Using `django_filters.ChoiceFilter` causes the Enums to be converted to strings in GraphQL filters.
This class uses GraphQL Enums instead, which gives better autocomplete results.

---

## IntegerChoiceFilter & IntegerMultipleChoiceFilter

Allows plain integers as choices in GraphQL filters. Normally, integer enums are converted
to string enums in GraphQL by prefixing them with `A_`, but this filter allows using plain integers.

[method filters]: https://django-filter.readthedocs.io/en/stable/guide/usage.html#customize-filtering-with-filter-method
