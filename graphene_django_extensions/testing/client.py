from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
import sqlparse
from django import db
from django.contrib.auth import get_user_model
from django.test import Client
from graphene_django.utils.testing import graphql_query

from ..typing import TypedDict

if TYPE_CHECKING:
    from collections.abc import Generator

    from django.contrib.auth.models import User
    from django.http import HttpResponse

    from ..typing import Any, Self


__all__ = [
    "GraphQLClient",
    "capture_database_queries",
]


class FieldError(TypedDict):
    field: str
    messages: list[str]


@dataclass
class QueryData:
    queries: list[str]

    @property
    def log(self) -> str:
        message = "-" * 75
        message += f"\n>>> Queries ({len(self.queries)}):\n"
        for index, query in enumerate(self.queries):
            message += f"{index + 1}) ".ljust(75, "-") + f"\n{query}\n"
        message += "-" * 75
        return message


class GQLResponse:
    def __init__(self, response: HttpResponse, query_data: QueryData) -> None:
        # 'django.test.client.Client.request' sets json attribute on the response.
        self.json: dict[str, Any] = response.json()  # type: ignore[attr-defined]
        self.query_data = query_data

    def __str__(self) -> str:
        return json.dumps(self.json, indent=2, sort_keys=True, default=str)

    def __repr__(self) -> str:
        return repr(self.json)

    def __len__(self) -> int:
        return len(self.edges)

    def __getitem__(self, item: str) -> dict[str, Any] | None:
        return (self.data or {})[item]

    def __contains__(self, item: str) -> bool:
        return item not in self.json

    @property
    def queries(self) -> list[str]:
        """Return a list of the database queries that were executed."""
        # Note: To use query counting, DEBUG needs to be set to True.
        return self.query_data.queries

    @property
    def query_log(self) -> str:
        """Return a string representation of the database queries that were executed."""
        # Note: To use query counting, DEBUG needs to be set to True.
        return self.query_data.log

    @property
    def data(self) -> dict[str, Any] | None:
        """Return the data from the response content."""
        return self.json["data"]

    @property
    def first_query_object(self) -> dict[str, Any] | None:
        """
        Return the first query object in the response content.

        >>> self.json = {"data": {"foo": {"name": "bar"}}}
        >>> self.first_query_object
        {"name": "bar"}
        """
        data = self.data or {}
        try:
            return next(iter(data.values()))
        except StopIteration:  # pragma: no cover
            pytest.fail(f"No query object not found in response content: {self.json}")

    @property
    def edges(self) -> list[dict[str, Any]]:
        """
        Return edges from the first query in the response content.

        >>> self.json = {"data": {"foo": {"edges": [{"node": {"name": "bar"}}]}}}
        >>> self.edges
        [{"node": {"name": "bar"}}]
        """
        try:
            return self.first_query_object["edges"]
        except (KeyError, TypeError):  # pragma: no cover
            pytest.fail(f"Edges not found in response content: {self.json}")

    def node(self, index: int = 0) -> dict[str, Any]:
        """
        Return the node at the given index in the response content edges.

        >>> self.json = {"data": {"foo": {"edges": [{"node": {"name": "bar"}}]}}}
        >>> self.node(0)
        {"name": "bar"}
        """
        try:
            return self.edges[index]["node"]
        except (IndexError, TypeError):  # pragma: no cover
            pytest.fail(f"Node {index!r} not found in response content: {self.json}")

    @property
    def has_errors(self) -> bool:  # pragma: no cover
        """Are there any errors in the response?"""
        # Errors in the root of the response
        if "errors" in self.json and self.json.get("errors") is not None:
            return True

        # Errors in the fields of the first query object
        if "errors" in (self.first_query_object or {}) and (self.first_query_object or {}).get("errors") is not None:
            return True

        return False

    @property
    def errors(self) -> list[dict[str, Any]]:
        """
        Return errors found in the root of the response.

        >>> self.json = {"errors": [{"locations": [...], "message": "bar", "path": [...]}]}
        >>> self.errors
        [{"locations": [...], "message": "bar", "path": [...]}]
        """
        try:
            return self.json["errors"]
        except (KeyError, TypeError):  # pragma: no cover
            pytest.fail(f"Errors not found in response content: {self.json}")

    def error_message(self, selector: int | str = 0) -> str:  # pragma: no cover
        """
        Return the error message from the errors list...

        1) in the given index

        >>> self.json = {"errors": [{"message": ["bar"], "path": [...]}]}
        >>> self.error_message(0)  # default
        "bar"

        2) in the given path:

        >>> self.json = {"errors": [{"message": ["bar"], "path": ["fizz", "buzz", "foo"]}]}
        >>> self.error_message("foo")
        "bar"
        """
        if isinstance(selector, int):
            try:
                return self.errors[selector]["message"]
            except IndexError:
                pytest.fail(f"Errors list doesn't have an index {selector}: {self.json}")
            except (KeyError, TypeError):
                pytest.fail(f"Field 'message' not found in error content: {self.json}")
        else:
            try:
                return next(error["message"] for error in self.errors if error["path"][-1] == selector)
            except StopIteration:
                pytest.fail(f"Errors list doesn't have an error for field '{selector}': {self.json}")
            except (KeyError, TypeError):
                pytest.fail(f"Field 'message' not found in error content: {self.json}")

    @property
    def field_errors(self) -> list[FieldError]:
        """
        Return errors for data fields.

        >>> self.json = {"data": {"foo": {"errors": [{"field": "bar", "message": ["baz"]}]
        >>> self.field_errors
        [{"field": "bar", "message": ["baz"]}]
        """
        try:
            return self.first_query_object["errors"]
        except (KeyError, TypeError):  # pragma: no cover
            pytest.fail(f"Field errors not found in response content: {self.json}")

    def field_error_messages(self, field: str = "nonFieldErrors") -> list[str]:  # pragma: no cover
        """
        Return field error messages for desired field.

        >>> self.json = {"errors": [{"field": "foo", "message": ["bar"]}]}
        >>> self.field_error_messages("foo")
        ["bar"]
        """
        for error in self.field_errors or []:
            if error.get("field") == field:
                try:
                    return error["messages"]
                except (KeyError, TypeError):
                    msg = f"Error message for field {field!r} not found in error: {error}"
                    pytest.fail(msg)

        msg = f"Error for field {field!r} not found in response content: {self.json}"
        raise pytest.fail(msg)

    def assert_query_count(self, count: int) -> None:  # pragma: no cover
        # Note: To use query counting, DEBUG needs to be set to True.
        assert len(self.queries) == count, self.query_log  # noqa: S101


class GraphQLClient(Client):
    def __call__(  # noqa: PLR0913
        self: Self,
        query: str,
        operation_name: str | None = None,
        input_data: dict[str, Any] | None = None,
        variables: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
    ) -> GQLResponse:
        """
        Make a GraphQL query to the test client.

        :params query: GraphQL query string.
        :params operation_name: Name of the operation to execute.
        :params input_data: Set (and override) the "input" variable in the given variables.
        :params variables: Variables for the query.
        :params headers: Headers for the query. Keys should in all-caps, and be prepended with "HTTP_".
        """
        with capture_database_queries() as results:
            response = graphql_query(
                query=query,
                operation_name=operation_name,
                input_data=input_data,
                variables=variables,
                headers=headers,
                client=self,
            )
        return GQLResponse(response, results)

    def login_with_superuser(self) -> User:
        user = get_user_model().objects.create_superuser(username="superuser", email="superuser@django.com")
        self.force_login(user)
        return user

    def login_with_regular_user(self) -> User:
        user = get_user_model().objects.create_user(username="user", email="user@django.com")
        self.force_login(user)
        return user


@contextmanager
def capture_database_queries() -> Generator[QueryData, None, None]:
    """Capture results of what database queries were executed. `DEBUG` needs to be set to True."""
    results = QueryData(queries=[])
    db.connection.queries_log.clear()

    try:
        yield results
    finally:
        results.queries = [
            sqlparse.format(query["sql"], reindent=True)
            for query in db.connection.queries
            if "sql" in query
            and not query["sql"].startswith("SAVEPOINT")
            and not query["sql"].startswith("RELEASE SAVEPOINT")
        ]
