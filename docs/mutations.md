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
- Adds an `errors = graphene.List(ErrorType)` field for returning errors.
- Formats errors raised from nested serializers.
- Can add permission checks via permission classes.
- Checks for missing object types for nested model serializer fields to avoid nebulous import order errors.

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
        fields = ["pk", "field"]

class MainSerializer(NestingModelSerializer):
    sub_entry = SubSerializer()

    class Meta:
        model = Main
        fields = ["pk", "sub_entry"]
```

When using the above serializers with the following data:

```json
{
    "pk": 1,
    "sub_entities": {
        "field": "value"
    }
}
```

This will create the Main entity and the Sub entity,
and link the Sub entity to the Main entity.

If instead this is used:

```json
{
    "pk": 1,
    "sub_entities": {
        "pk": 2
    }
}
```

This will create the Main entity and link an existing Sub entity with `pk=2` to it.
If the Sub entity does not exist, a 404 error will be raised. If the sub entity
is already linked to another Main entity, this will be a no-op.

If the `pk` field is included with some other fields, the Sub entity will also be updated:

```json
{
    "pk": 1,
    "sub_entities": {
        "pk": 2,
        "field": "value"
    }
}
```

For `to_many` relations, the serializer field must be a ListSerializer:

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
        {"field": "value"}
    ]
}
```
