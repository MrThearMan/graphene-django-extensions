from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from django.contrib.auth import get_user_model
from django.test.client import MULTIPART_CONTENT, Client
from graphene_django.settings import graphene_settings

from ..files import extract_files
from .utils import QueryData, capture_database_queries

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from django.core.files import File
    from django.http import HttpResponse

    from ..typing import Any, ClassVar, FieldError, Self

__all__ = [
    "GraphQLClient",
]


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
        return self.query_data.queries

    @property
    def query_log(self) -> str:
        """Return a string representation of the database queries that were executed."""
        return self.query_data.log

    @property
    def data(self) -> dict[str, Any] | None:
        """Return the data from the response content."""
        return self.json["data"]

    @property
    def first_query_object(self) -> dict[str, Any] | list[Any] | None:
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
            msg = f"No query object not found in response content: {self.json}"
            pytest.fail(msg, pytrace=False)

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
            msg = f"Edges not found in response content: {self.json}"
            pytest.fail(msg, pytrace=False)

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
            msg = f"Node {index!r} not found in response content: {self.json}"
            pytest.fail(msg, pytrace=False)

    @property
    def has_errors(self) -> bool:  # pragma: no cover
        """Are there any errors in the response?"""
        return "errors" in self.json and self.json.get("errors") is not None

    @property
    def errors(self) -> list[dict[str, Any]]:
        """
        Return all errors.

        >>> self.json = {"errors": [{"message": "bar", "path": [...], ...}]}
        >>> self.errors
        [{"message": "bar", "path": [...], ...}]
        """
        try:
            return self.json["errors"]
        except (KeyError, TypeError):  # pragma: no cover
            msg = f"Errors not found in response content: {self.json}"
            pytest.fail(msg, pytrace=False)

    def error_message(self, selector: int | str = 0) -> str:  # pragma: no cover
        """
        Return the error message from the errors list...

        1) in the given index

        >>> self.json = {"errors": [{"message": "bar", ...}]}
        >>> self.error_message(0)  # default
        "bar"

        2) in the given path:

        >>> self.json = {"errors": [{"message": "bar", "path": ["fizz", "buzz", "foo"], ...}]}
        >>> self.error_message("foo")
        "bar"
        """
        if isinstance(selector, int):
            try:
                return self.errors[selector]["message"]
            except IndexError:
                msg = f"Errors list doesn't have an index {selector}: {self.json}"
                pytest.fail(msg, pytrace=False)
            except (KeyError, TypeError):
                msg = f"Field 'message' not found in error content: {self.json}"
                pytest.fail(msg, pytrace=False)
        else:
            try:
                return next(error["message"] for error in self.errors if error["path"][-1] == selector)
            except StopIteration:
                msg = f"Errors list doesn't have an error for field '{selector}': {self.json}"
                pytest.fail(msg, pytrace=False)
            except (KeyError, TypeError):
                msg = f"Field 'message' not found in error content: {self.json}"
                pytest.fail(msg, pytrace=False)

    @property
    def field_errors(self) -> list[FieldError]:
        """
        Return all field error messages.

        >>> self.json = {
        ...     "errors": [
        ...         {
        ...             "extensions": {
        ...                 "errors": [
        ...                     {
        ...                         "field": "foo",
        ...                         "messages": ["bar"],
        ...                         "codes": ["baz"],
        ...                     },
        ...                 ],
        ...             },
        ...         },
        ...     ],
        ... }
        ...
        >>> self.field_errors
        [{"field": "foo", "messages": ["bar"], "codes": ["baz"]}]
        """
        try:
            return [error for item in self.errors for error in item.get("extensions", {}).get("errors", [])]
        except (KeyError, TypeError):  # pragma: no cover
            msg = f"Field errors not found in response content: {self.json}"
            pytest.fail(msg, pytrace=False)

    def field_error_messages(self, field: str = "nonFieldErrors") -> list[str]:  # pragma: no cover
        """
        Return field error messages for desired field.

        >>> self.json = {
        ...     "errors": [
        ...         {
        ...             "extensions": {
        ...                 "errors": [
        ...                     {
        ...                         "field": "foo",
        ...                         "messages": "bar",
        ...                         "codes": "baz",
        ...                     },
        ...                     {
        ...                         "field": "foo",
        ...                         "messages": "one",
        ...                         "codes": "",
        ...                     },
        ...                 ],
        ...             },
        ...         },
        ...     ],
        ... }
        ...
        >>> self.field_error_messages("foo")
        ["bar", "one"]
        """
        messages: list[str] = []
        for error in self.field_errors:
            if error.get("field") == field:
                try:
                    messages.append(error["message"])
                except (KeyError, TypeError):
                    msg = f"Error message for field {field!r} not found in error: {error}"
                    pytest.fail(msg, pytrace=False)

        return messages

    def error_code(self, selector: int | str = 0) -> str:  # pragma: no cover
        """
        Return the error code from the errors list.

        1) in the given index

        >>> self.json = {"errors": [{"extensions": {"code": "bar"}, ...}]}
        >>> self.error_code(0)  # default
        "bar"

        2) in the given path:

        >>> self.json = {"errors": [{"extensions": {"code": "bar"}, "path": ["fizz", "buzz", "foo"], ...}]}
        >>> self.error_code("foo")
        "bar"
        """
        if isinstance(selector, int):
            try:
                return self.errors[selector]["extensions"]["code"]
            except (KeyError, TypeError):
                msg = f"Error code not found in error content: {self.json}"
                pytest.fail(msg, pytrace=False)
        else:
            try:
                return next(error["extensions"]["code"] for error in self.errors if error["path"][-1] == selector)
            except StopIteration:
                msg = f"Errors list doesn't have an error for field '{selector}': {self.json}"
                pytest.fail(msg, pytrace=False)
            except (KeyError, TypeError):
                msg = f"Field 'extensions' not found in error content: {self.json}"
                pytest.fail(msg, pytrace=False)

    def field_error_codes(self, field: str = "nonFieldErrors") -> list[str]:  # pragma: no cover
        """
        Return field error codes for desired field.

        >>> self.json = {
        ...     "errors": [
        ...         {
        ...             "extensions": {
        ...                 "errors": [
        ...                     {
        ...                         "field": "foo",
        ...                         "messages": "bar",
        ...                         "codes": "baz",
        ...                     },
        ...                     {
        ...                         "field": "foo",
        ...                         "messages": "one",
        ...                         "codes": "",
        ...                     },
        ...                 ],
        ...             },
        ...         },
        ...     ],
        ... }
        ...
        >>> self.field_error_codes("foo")
        ["bar", ""]
        """
        codes: list[str] = []
        for error in self.field_errors:
            if error.get("field") == field:
                try:
                    codes.append(error["code"])
                except (KeyError, TypeError):
                    msg = f"Error code for field {field!r} not found in error: {error}"
                    pytest.fail(msg, pytrace=False)

        return codes

    def assert_query_count(self, count: int) -> None:  # pragma: no cover
        if len(self.queries) != count:
            msg = f"Expected {count} queries, got {len(self.queries)}.\n{self.query_log}"
            pytest.fail(msg, pytrace=False)


class GraphQLClient(Client):
    response_class: ClassVar[type[GQLResponse]] = GQLResponse

    def __call__(  # noqa: PLR0913
        self: Self,
        query: str,
        input_data: dict[str, Any] | None = None,
        variables: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        operation_name: str | None = None,
    ) -> GQLResponse:
        """
        Make a GraphQL query to the test client.

        :params query: GraphQL query string.
        :params input_data: Set (and override) the "input" variable in the given variables.
        :params variables: Variables for the query.
        :params headers: Headers for the query.
        :params operation_name: Name of the operation to execute.
        """
        variables: dict[str, Any] = variables or {}
        if input_data is not None:
            variables.update({"input": input_data})

        files = extract_files(variables, prefix="variables")

        path_map: dict[str, list[str]] = {}
        files_map: dict[str, File] = {}
        for i, (file, path) in enumerate(files.items()):
            path_map[str(i)] = path
            files_map[str(i)] = file

        body: dict[str, Any] = {"query": query}
        if variables:
            body["variables"] = variables
        if operation_name is not None:  # pragma: no cover
            body["operationName"] = operation_name

        data = json.dumps(body)
        if files:
            data = {
                "operations": data,
                "map": json.dumps(path_map),
                **files_map,
            }

        with capture_database_queries() as results:
            response: HttpResponse = self.post(  # type: ignore[assignment]
                path=graphene_settings.TESTING_ENDPOINT,
                data=data,
                content_type=MULTIPART_CONTENT if files else "application/json",
                headers=headers,
            )

        return self.response_class(response, results)

    def login_with_superuser(self) -> User:
        user = get_user_model().objects.create_superuser(username="superuser", email="superuser@django.com")
        self.force_login(user)
        return user

    def login_with_regular_user(self) -> User:
        user = get_user_model().objects.create_user(username="user", email="user@django.com")
        self.force_login(user)
        return user
