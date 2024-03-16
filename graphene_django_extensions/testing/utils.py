from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from functools import partial
from inspect import cleandoc
from io import BytesIO
from typing import Any, Callable, Generator, NamedTuple, TypedDict, TypeVar

import pytest
import sqlparse
from django import db
from django.core.files import File

__all__ = [
    "capture_database_queries",
    "compare_unordered",
    "create_mock_png",
    "parametrize_helper",
]


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


def create_mock_png() -> File:
    from PIL import Image

    bytes_io = BytesIO()
    img = Image.new("RGB", (1, 1))
    img.save(bytes_io, format="PNG", compress_level=1)
    bytes_io.seek(0)
    return File(bytes_io, name="image.png")
