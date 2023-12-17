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

## EnumChoiceFilter & EnumMultipleChoiceFilter

Custom fields for handling enums better in GraphQL filters.
Using `django_filters.ChoiceFilter` causes the Enums to be converted to strings in GraphQL filters.
This class uses GraphQL Enums instead, which gives better autocomplete results.

---

## IntegerChoiceFilter & IntegerMultipleChoiceFilter

Allows plain integers as choices in GraphQL filters. Normally, integer enums are converted
to string enums in GraphQL by prefixing them with `A_`, but this filter allows using plain integers.

[method filters]: https://django-filter.readthedocs.io/en/stable/guide/usage.html#customize-filtering-with-filter-method
