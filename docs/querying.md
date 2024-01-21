# Queries

## DjangoNode

Custom base class for GraphQL ObjectTypes that are backed by a Django model.

```python
from graphene_django_extensions import DjangoNode
from example.models import Example

class MyNode(DjangoNode):
    class Meta:
        model = Example
        fields = [...]
```

Extends form `graphene_django.types.DjangoObjectType` and adds the following features:

- Makes the `graphene.relay.Node` interface the default interface for the type.
- Adds `total_count = graphene.Int()` field to the default Connection field for the type.
- Adds `pk` primary key field and resolver  to the ObjectType, if present in `Meta.fields`.
- Can add permission checks via permission classes.

### Permission errors

If a permission check for a query fails, an error like this will be raised:

```json
{
    "errors": [
        {
            "message": "No permission to access node.",
            "path": ["examples"],
            "extensions": {"code": "NODE_PERMISSION_DENIED"},
            "locations": [{"line": 1, "column": 63}]
        }
    ]
}
```

The message and code depends on the operation type, and can be changed using the following settings.

| Operation       | Message setting                   | Message default               | Code setting                   | Code default             |
|-----------------|-----------------------------------|-------------------------------|--------------------------------|--------------------------|
| field/node      | `QUERY_PERMISSION_ERROR_MESSAGE`  | No permission to access node. | `QUERY_PERMISSION_ERROR_CODE`  | NODE_PERMISSION_DENIED   |
| list/connection | `FILTER_PERMISSION_ERROR_MESSAGE` | No permission to access node. | `FILTER_PERMISSION_ERROR_CODE` | FILTER_PERMISSION_DENIED |

More on permissions on the [permissions page].

---

### Interface

Some new methods are also added. Here are the most useful ones:

#### filter_queryset

- args:
    - `queryset: QuerySet`
    - `info: GQLInfo`

Can be used to filter available rows for both `get_queryset` and `get_node`.

#### Field

- args:
    - `kwargs: dict[str, Any]`

Create a 'regular' Field from the type.

#### RelatedField

- args:
    - `kwargs: dict[str, Any]`

Create a one-to-one or many-to-one related Field from the type.

#### ListField

- args:
    - `kwargs: dict[str, Any]`

Create a DjangoListField from the type.

#### Node

- args:
    - `kwargs: dict[str, Any]`

Create a Relay Node from the type.

#### Connection

- args:
    - `kwargs: dict[str, Any]`

Create a Relay Connection Field from the type.

---

Subclasses can be configured through the `Meta`-class. Here are the most useful options:

| Option               | Type                         | Description                                                                                 |
|----------------------|------------------------------|---------------------------------------------------------------------------------------------|
| `model`              | `type[Model]`                | Required. The model class for the node.                                                     |
| `fields`             | `list[str]` or `__all__`     | Required. The fields to include in the node. If `__all__` is used, all fields are included. |
| `filterset_class`    | `type[FilterSet]`            | Optional. The FilterSet class to use for filtering the ObjectType queryset.                 |
| `permission_classes` | `list[type[BasePermission]]` | Optional. Set [permission classes] for the node. Defaults to (`AllowAny`,).                 |
| `restricted_fields`  | `dict[str, PermCheck]`       | Optional. Adds [permission checks] to the resolvers of the fields as defined in the dict.   |


[permissions page]: https://mrthearman.github.io/graphene-django-extensions/permissions/
[permission classes]: https://mrthearman.github.io/graphene-django-extensions/permissions/#permission-classes
[permission checks]: https://mrthearman.github.io/graphene-django-extensions/permissions/#restricted-fields
