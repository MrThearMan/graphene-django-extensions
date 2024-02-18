# Mutations

## DjangoMutation

Custom base class for GraphQL-mutations that are backed by a Django model.
Has three subclasses: `CreateMutation`, `UpdateMutation` and `DeleteMutation`,
which should cover most use cases, but custom mutations can also be created.

```python
from graphene_django_extensions import CreateMutation, UpdateMutation, DeleteMutation

class ExampleCreateMutation(CreateMutation):
    class Meta:
        model = Example
        serializer_class = ExampleSerializer

class ExampleUpdateMutation(UpdateMutation):
    class Meta:
        model = Example
        serializer_class = ExampleSerializer

class ExampleDeleteMutation(DeleteMutation):
    class Meta:
        model = Example
```

Adds the following features to all types that inherit it:

- For update operations, converts all fields to optional fields, enabling partial updates.
- Can add permission checks via permission classes.
- Converts and formats errors raised from serializers (also nested ones) into GraphQL errors.
- Checks for missing object types for nested model serializer fields to avoid nebulous import order errors.

### Permission errors

If a permission check for a mutation fails, an error like this will be raised:

```json
{
    "errors": [
        {
            "message": "No permission to create.",
            "path": ["createExample"],
            "extensions": {"code": "CREATE_PERMISSION_DENIED"},
            "locations": [{"line": 1, "column": 63}]
        }
    ]
}
```

The message and code depends on the operation type, and can be changed using the following settings.

| Operation | Message setting                     | Message default          | Code setting                     | Code default                 |
|-----------|-------------------------------------|--------------------------|----------------------------------|------------------------------|
| create    | `CREATE_PERMISSION_ERROR_MESSAGE`   | No permission to create. | `CREATE_PERMISSION_ERROR_CODE`   | `CREATE_PERMISSION_DENIED`   |
| update    | `UPDATE_PERMISSION_ERROR_MESSAGE`   | No permission to update. | `UPDATE_PERMISSION_ERROR_CODE`   | `UPDATE_PERMISSION_DENIED`   |
| delete    | `DELETE_PERMISSION_ERROR_MESSAGE`   | No permission to delete. | `DELETE_PERMISSION_ERROR_CODE`   | `DELETE_PERMISSION_DENIED`   |
| custom    | `MUTATION_PERMISSION_ERROR_MESSAGE` | No permission to mutate. | `MUTATION_PERMISSION_ERROR_CODE` | `MUTATION_PERMISSION_DENIED` |

More on permissions on the [permissions page].

### Field level errors

If a mutation serializer raises a `ValidationError`, the errors will be converted into a
single GraphQL error with all the individual field error messages and codes included:

```json
{
    "errors": [
        {
            "message": "Mutation was unsuccessful.",
            "path": ["createExample"],
            "extensions": {
                "code": "MUTATION_VALIDATION_ERROR",
                "errors": [
                    {
                        "field": "number",
                        "message": "Number must be positive.",
                        "code": "invalid"
                    },
                    {
                        "field": "number",
                        "message": "Number must be an even.",
                        "code": ""
                    },
                    {
                        "field": "text",
                        "message": "Text must be at least 10 characters long.",
                        "code": "invalid"
                    }
                ]
            },
            "locations": [{"line": 1, "column": 63}]
        }
    ]
}
```

If the error is raised from a nested serializer (when creating sub entities along with the parent entity, see
`NestingModelSerializer` below), the field will include the dotted path to the sub entity where the field is located:

```json
{
    "errors": [
        {
            "message": "Mutation was unsuccessful.",
            "path": ["createExample"],
            "extensions": {
                "code": "MUTATION_VALIDATION_ERROR",
                "errors": [
                    {
                        "field": "subEntry.number",
                        "message": "Number must be positive.",
                        "code": "invalid"
                    }
                ]
            },
            "locations": [{"line": 1, "column": 63}]
        }
    ]
}
```

---

The following options can be set in the `Meta`-class.

| Option                    | Type                         | Description                                                                                                                                                                                                                                 |
|---------------------------|------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `model`                   | `type[Model]`                | Required (delete only). Model class for the model the operation is performed on.                                                                                                                                                            |
| `serializer_class`        | `type[ModelSerializer]`      | Required (create and update only). The serializer used for the mutation.                                                                                                                                                                    |
| `output_serializer_class` | `type[ModelSerializer]`      | Optional. The serializer used for the output data. If not set, `serializer_class` is used. Serializer fields are modified so that all fields are optional, enabling partial updates.                                                        |
| `permission_classes`      | `list[type[BasePermission]]` | Optional. Set permission classes for the mutation. Defaults to (`AllowAny`,).                                                                                                                                                               |
| `lookup_field`            | `str`                        | Optional. The field used for looking up the instance to be mutated. Defaults to the object's primary key, which is usually `id`. Note that the `lookup_field` attribute has to be available from the serializer's `Meta.fields` definition. |
| `form_class`              | `type[ModelForm]`            | Optional. Can be used instead of `serializer_class`.                                                                                                                                                                                        |
| `output_form_class`       | `type[ModelForm]`            | Optional. Can be used instead of `output_serializer_class`                                                                                                                                                                                  |

---

### Custom mutations

Custom mutations can be created by subclassing `DjangoMutation` and implementing
the `custom_mutation` method. `serializer_class` and `output_serializer_class` can be
set in the `Meta`-class, and will be converted to the mutation's input and output types.
If `output_serializer_class` is not set, `serializer_class` will be used for both input
and output types.

```python
from graphene_django_extensions.bases import DjangoMutation

class ExampleCustomMutation(DjangoMutation):
    class Meta:
        serializer_class = ExampleInputSerializer
        output_serializer_class = ExampleOutputSerializer

    @classmethod
    def custom_mutation(cls, info, **kwargs):
        # Do custom logic here.
        # `kwargs` have already been validated by the serializer.
        return cls(...)
```

> Like model mutations, `form_class` and `output_form_class` can be used instead of
> `serializer_class` and `output_serializer_class`.

---

## NestingModelSerializer

A custom `ModelSerializer` that contains logic for updating and creating related models
when they are included as nested serializer fields:

```python
from graphene_django_extensions import NestingModelSerializer

class SubSerializer(NestingModelSerializer):
    class Meta:
        model = Sub
        fields = ["pk", "sub_field"]

class MainSerializer(NestingModelSerializer):
    sub_entry = SubSerializer()

    class Meta:
        model = Main
        fields = ["pk", "main_field", "sub_entry"]
```

When using the above serializers with the following data:

```json
{
    "main_field": "foo",
    "sub_entities": {
        "sub_field": "bar"
    }
}
```

This will create the Main entity and the Sub entity, and link the Sub entity to the Main entity.

If instead this is used:

```json
{
    "pk": 1,
    "sub_entities": {
        "sub_field": "bar"
    }
}
```

This will update the Main entity with `pk=1`, and create a new Sub entity and link it to the Main entity.

We can also link an existing Sub entity to the Main entity on update or create:

```json
{
    "main_field": "foo",
    "sub_entities": {
        "pk": 2
    }
}
```

If the Sub entity does not exist, a 404 error will be raised. If the sub entity
is already linked to another Main entity, this will be a no-op.

If the `pk` field is included in the subquery, the existing Sub entity will be updated:

```json
{
    "main_field": "foo",
    "sub_entities": {
        "pk": 2,
        "sub_field": "value"
    }
}
```

For `to_many` relations, the serializer field must use `many=True`:

```python
class MainSerializer(NestingModelSerializer):
    sub_entry = SubSerializer(many=True)
```

Same logic applies for `to_many` relations, but if the relation is a `one_to_many` relation,
and the relation is updated, any existing related entities that were not included in the request
will be deleted (e.g. Sub entity with `pk=1` could have been deleted here):

```json
{
    "pk": 1,
    "sub_entities": [
        {"pk": 2},
        {"sub_field": "value"}
    ]
}
```

[permissions page]: https://mrthearman.github.io/graphene-django-extensions/permissions/
