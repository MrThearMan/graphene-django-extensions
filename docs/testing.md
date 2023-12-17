# Testing tools

## build_query

- args:
    - `__name`: Name of the query, in camelCase.
    - `fields`: Field selections as a GraphQL string.
    - `connection`: Whether to build a Relay Connection query or basic one.
    - `**filter_params`: Parameters to use in the query. Will be converted to camelCase.
      Use `__` to add filters to fields instead of the query.

Used to build GraphQL queries for testing.

---

## build_mutation

- args:
    - `__name`: Name of the mutation, in camelCase.
    - `__mutation_class_name`: Name of the mutation ObjectType, in PascalCase.
    - `fields`: Field selections as a GraphQL string.

Used to build GraphQL mutations for testing.

---

## GraphQLClient

Testing client with a convenient response object and database query counting.
Can be accessed through `graphql` fixture. The query counting can be accessed
separately via `query_counter` fixture.
