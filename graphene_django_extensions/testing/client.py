from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass
from functools import partial
from inspect import cleandoc
from typing import TYPE_CHECKING

import pytest
import sqlparse
from django import db
from django.contrib.auth import get_user_model
from django.test import Client
from graphene_django.utils.testing import graphql_query

from ..typing import NamedTuple, TypedDict, TypeVar

if TYPE_CHECKING:
    from collections.abc import Generator

    from django.contrib.auth.models import User
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.http import HttpResponse

    from ..typing import Any, Callable, FieldError, Self

__all__ = [
    "GraphQLClient",
    "capture_database_queries",
    "parametrize_helper",
    "compare_unordered",
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
    def __call__(  # noqa: PLR0913
        self: Self,
        query: str,
        operation_name: str | None = None,
        input_data: dict[str, Any] | None = None,
        variables: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
        files: dict[str, SimpleUploadedFile] | None = None,
    ) -> GQLResponse:
        """
        Make a GraphQL query to the test client.

        :params query: GraphQL query string.
        :params operation_name: Name of the operation to execute.
        :params input_data: Set (and override) the "input" variable in the given variables.
        :params variables: Variables for the query.
        :params headers: Headers for the query. Keys should in all-caps, and be prepended with "HTTP_".
        :params files: Files to be uploaded with the query. Requires `graphene-file-upload`.
        """
        with capture_database_queries() as results:
            if files is not None:  # pragma: no cover
                from graphene_file_upload.django.testing import file_graphql_query

                response = file_graphql_query(
                    query=query,
                    op_name=operation_name,
                    input_data=input_data,
                    variables=variables,
                    headers=headers,
                    files=files,
                    client=self,
                )
            else:
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


@dataclass
class QueryData:
    queries: list[str]

    @property
    def log(self) -> str:
        message = "-" * 75
        message += f"\n>>> Queries ({len(self.queries)}):\n"
        for index, query in enumerate(self.queries):
            formatted_query = sqlparse.format(query, reindent=True)
            message += f"{index + 1}) ".ljust(75, "-") + f"\n{formatted_query}\n"
        message += "-" * 75
        return message


def _db_query_logger(  # noqa: PLR0913
    execute: Callable[..., Any],
    sql: str,
    params: tuple[Any, ...],
    many: bool,  # noqa: FBT001
    context: dict[str, Any],
    # Added with functools.partial()
    query_cache: list[str],
) -> Any:
    """
    A database query logger for capturing executed database queries.
    Used to check that query optimizations work as expected.

    Can also be used as a place to put debugger breakpoint for solving issues.
    """
    # Don't include transaction creation, as we aren't interested in them.
    if not sql.startswith("SAVEPOINT") and not sql.startswith("RELEASE SAVEPOINT"):
        try:
            query_cache.append(sql % params)
        except TypeError:  # pragma: no cover
            query_cache.append(sql)
    return execute(sql, params, many, context)


@contextmanager
def capture_database_queries() -> Generator[QueryData, None, None]:
    """Capture results of what database queries were executed. `DEBUG` needs to be set to True."""
    results = QueryData(queries=[])
    query_logger = partial(_db_query_logger, query_cache=results.queries)

    with db.connection.execute_wrapper(query_logger):
        yield results


TNamedTuple = TypeVar("TNamedTuple", bound=NamedTuple)


class ParametrizeArgs(TypedDict):
    argnames: list[str]
    argvalues: list[TNamedTuple]
    ids: list[str]


def parametrize_helper(__tests: dict[str, TNamedTuple], /) -> ParametrizeArgs:
    """Construct parametrize input while setting test IDs."""
    assert __tests, "I need some tests, please!"  # noqa: S101
    values = list(__tests.values())
    try:
        return ParametrizeArgs(
            argnames=list(values[0].__class__.__annotations__),
            argvalues=values,
            ids=list(__tests),
        )
    except AttributeError as error:  # pragma: no cover
        msg = "Improper configuration. Did you use a NamedTuple for TNamedTuple?"
        raise RuntimeError(msg) from error


def _dict_sorter(data: dict[str, Any]) -> tuple[str, str]:
    return str(data.keys()), str(data.values())


class ComparisonError(Exception):
    errors_by_code: dict[int, str] = {
        1: "type mismatch",
        2: "value mismatch",
        3: "dict keys mismatch",
        4: "array length mismatch",
        5: "array content mismatch",
        6: "array type mismatch",
    }

    def __init__(self, actual: Any, expected: Any, *, reason_code: int) -> None:
        self.actual = actual
        self.expected = expected
        self.actual_key = ""
        self.expected_key = ""
        self.reason = self.errors_by_code[reason_code]


def compare_unordered(actual: dict[str, Any] | list[Any], expected: dict[str, Any] | list[Any]) -> None:
    """
    Compare two json data structures without caring about the order in which items appear in lists.

    If the comparison fails, will raise a `pytest.fail` with an error message
    which will try to point out the place where the comparison failed.
    However, this will not always pick the best "nodes" to show, so
    full comparison data will also be shown in the error message for clarity.

    Disclaimer: Cannot compare json with heterogeneous lists.
    """
    msg: str = ""
    try:
        _compare_unordered(actual, expected)
    except ComparisonError as error:
        msg = cleandoc(
            f"""
            Actual and expected data don't match ({error.reason}):
                actual{error.actual_key} = {error.actual}
                expected{error.expected_key} = {error.expected}
            """
        )
        if error.actual_key or error.expected_key:
            msg = (
                msg
                + "\n"
                + cleandoc(
                    f"""
                    Full data:
                        actual = {actual}
                        expected = {expected}
                    """
                )
            )
    finally:
        if msg:
            pytest.fail(msg, pytrace=False)


def _compare_unordered(actual: Any, expected: Any) -> None:  # noqa: PLR0912, C901
    if type(actual) is not type(expected):
        raise ComparisonError(actual, expected, reason_code=1)

    if isinstance(actual, dict):
        if actual.keys() != expected.keys():
            raise ComparisonError(actual, expected, reason_code=3)

        for key in actual:
            try:
                _compare_unordered(actual[key], expected[key])
            except ComparisonError as error:  # noqa: PERF203
                error.actual_key = f"['{key}']{error.actual_key}"
                error.expected_key = f"['{key}']{error.expected_key}"
                raise

    elif isinstance(actual, list):
        if len(actual) != len(expected):
            raise ComparisonError(actual, expected, reason_code=4)

        actual_types = {type(item) for item in actual}
        expected_types = {type(item) for item in expected}

        if len(actual_types) != 1 or len(expected_types) != 1:
            raise ComparisonError(actual, expected, reason_code=6)

        actual_type = actual_types.pop()
        expected_type = expected_types.pop()
        if actual_type is not expected_type:
            raise ComparisonError(actual, expected, reason_code=5)

        if issubclass(actual_type, dict):
            for act, exp in zip(sorted(actual, key=_dict_sorter), sorted(expected, key=_dict_sorter)):
                try:
                    _compare_unordered(act, exp)
                except ComparisonError as error:  # noqa: PERF203
                    error.actual_key = f"[-]{error.actual_key}"
                    error.expected_key = f"[-]{error.expected_key}"
                    raise
        else:
            for act, exp in zip(sorted(actual), sorted(expected)):
                try:
                    _compare_unordered(act, exp)
                except ComparisonError as error:  # noqa: PERF203
                    error.actual_key = f"[-]{error.actual_key}"
                    error.expected_key = f"[-]{error.expected_key}"
                    raise

    elif actual != expected:
        raise ComparisonError(actual, expected, reason_code=2)
