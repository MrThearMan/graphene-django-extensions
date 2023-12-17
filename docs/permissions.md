# Permissions

## Permissions classes

Implements [graphene-permissions] style permission classes.

These methods can be overridden in subclasses to implement custom permissions:

#### has_permission

- args:
    - `user: AnyUser`

This is the main method for checking permissions. `has_node_permission`, `has_filter_permission`,
and `has_mutation_permission` will default to this if not overridden.

#### has_node_permission

- args:
    - `user: AnyUser`
    - `pk: Any`
    - `filters: dict[str, Any]`

Override this method to add specific permissions to a Relay Node field defined of a `DjangoNode`.

#### has_filter_permission

- args:
    - `user: AnyUser`
    - `filters: dict[str, Any]`

Override this method to add specific permissions to a Relay Connection field defined of a `DjangoNode`.

#### has_mutation_permission

- args:
    - `user: AnyUser`
    - `obj: Model`
    - `input_data: dict[str, Any]`
    - `filters: dict[str, Any]`

Override this method to add specific permissions to all mutations. `has_create_permission`,
`has_update_permission`, and `has_delete_permission` will default to this if not overridden.

#### has_create_permission

- args:
    - `user: AnyUser`
    - `obj: Model`
    - `input_data: dict[str, Any]`
    - `filters: dict[str, Any]`

Override this method to add specific permissions to a create mutation defined by `CreateMutation`.

#### has_update_permission

- args:
    - `user: AnyUser`
    - `obj: Model`
    - `input_data: dict[str, Any]`
    - `filters: dict[str, Any]`

Override this method to add specific permissions to an update mutation defined by `UpdateMutation`.

#### has_delete_permission

- args:
    - `user: AnyUser`
    - `obj: Model`
    - `input_data: dict[str, Any]`
    - `filters: dict[str, Any]`

Override this method to add specific permissions to a delete mutation defined by `DeleteMutation`.

---

## Restricted fields

To add more fine-grained permissions to individual fields, the `restricted_field` decorator can be used
on field resolvers. This will perform the permission check before the resolver is called, and raise
an `PermissionDenied` exception if the permission check fails.

There are two allowed interfaces for permissions checks:

```python
def permission_check(user: AnyUser) -> bool:
    ...
```

or

```python
def permission_check(user: AnyUser, instance: Model) -> bool:
    ...
```

...where the instance is the instance of the model that the field resolver is being called on.

When using `DjangoNode`, the `Meta.restricted_fields` option can be used to add permission checks
without having to use the decorator on each field resolver.

```python
from graphene_django_extensions import DjangoNode
from graphene_django_extensions.permissions import restricted_field

class ExampleNode(DjangoNode):

    class Meta:
        model = Example
        fields = ["example_field"]
        # Option 1
        restricted_fields = {
            "example_field": lambda user: user.is_authenticated,
        }

    # Option 2
    @restricted_field(lambda user: user.is_authenticated)
    def resolve_example_field(root: Example, info: GQLInfo):
        return root.example_field

```

[graphene-permissions]: https://github.com/redzej/graphene-permissions
