# Graphene Django Extensions

[![Coverage Status][coverage-badge]][coverage]
[![GitHub Workflow Status][status-badge]][status]
[![PyPI][pypi-badge]][pypi]
[![GitHub][licence-badge]][licence]
[![GitHub Last Commit][repo-badge]][repo]
[![GitHub Issues][issues-badge]][issues]
[![Downloads][downloads-badge]][pypi]
[![Python Version][version-badge]][pypi]

```shell
pip install graphene-django-extensions
```

---

**Documentation**: [https://mrthearman.github.io/graphene-django-extensions/](https://mrthearman.github.io/graphene-django-extensions/)

**Source Code**: [https://github.com/MrThearMan/graphene-django-extensions/](https://github.com/MrThearMan/graphene-django-extensions/)

**Contributing**: [https://github.com/MrThearMan/graphene-django-extensions/blob/main/CONTRIBUTING.md](https://github.com/MrThearMan/graphene-django-extensions/blob/main/CONTRIBUTING.md)

---

Extensions for writing GraphQL schemas with the [graphene-django] library with less boilerplate.

The main features are:

- A new ObjectType `DjangoNode`, which:
    - adds convenience methods for managing permissions for both the ObjectType and individual fields.
    - adds a hook for adding filtering to both single items and lists returned by the ObjectType.
    - adds convenience methods for creating Fields, ListFields, Nodes, and Connections for the ObjectType.
    - adds filterset filters automatically to ListFields created for the ObjectType.
    - automatically optimizes queries using [graphene-django-query-optimizer].

- A new MutationType `DjangoMutation`, which:
    - adds convenience methods for managing permissions.
    - adds `create`, `update` operation with serializers and `delete` operations with optional validation hook.
    - adds an option for custom model operations.
    - makes updates fully partial by default.
    - adds better error handling.

- A new ModelSerializer `NestingModelSerializer`, which:
    - adds pre and post save handlers for creating or updating related entities from nested serializer fields,
      all within a single transaction to ensure atomicity.
    - adds better handling of constraint integrity errors by finding `violation_error_message` from the constraint.
    - adds `get_or_default` method for finding default values for field validation.

- A new FilterSet `ModelFilterSet`, which:
    - changes the default filters for related fields to the custom `IntChoiceFilter` and `IntMultipleChoiceFilter`
      filters, which don't make database queries to check if the given primary keys for the filters actually
      correspond to existing rows for the database model.
    - adds a custom ordering filter automatically to all subclasses, with the default `pk` filter.
    - allows adding new ordering filters with the `Meta.order_by` attribute.
    - `order_by` fields are converted to enums for better autocompletion in GraphiQL.
    - allows combining multiple method filters with the `Meta.combination_methods` attribute.


[coverage-badge]: https://coveralls.io/repos/github/MrThearMan/graphene-django-extensions/badge.svg?branch=main
[status-badge]: https://img.shields.io/github/actions/workflow/status/MrThearMan/graphene-django-extensions/test.yml?branch=main
[pypi-badge]: https://img.shields.io/pypi/v/graphene-django-extensions
[licence-badge]: https://img.shields.io/github/license/MrThearMan/graphene-django-extensions
[repo-badge]: https://img.shields.io/github/last-commit/MrThearMan/graphene-django-extensions
[issues-badge]: https://img.shields.io/github/issues-raw/MrThearMan/graphene-django-extensions
[version-badge]: https://img.shields.io/pypi/pyversions/graphene-django-extensions
[downloads-badge]: https://img.shields.io/pypi/dm/graphene-django-extensions

[coverage]: https://coveralls.io/github/MrThearMan/graphene-django-extensions?branch=main
[status]: https://github.com/MrThearMan/graphene-django-extensions/actions/workflows/test.yml
[pypi]: https://pypi.org/project/graphene-django-extensions
[licence]: https://github.com/MrThearMan/graphene-django-extensions/blob/main/LICENSE
[repo]: https://github.com/MrThearMan/graphene-django-extensions/commits/main
[issues]: https://github.com/MrThearMan/graphene-django-extensions/issues

[graphene-django]: https://github.com/graphql-python/graphene-django
[graphene-django-query-optimizer]: https://github.com/MrThearMan/graphene-django-query-optimizer
