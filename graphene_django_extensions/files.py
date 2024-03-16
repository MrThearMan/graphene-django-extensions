"""
File upload handling utilities.

Compliant with the GraphQL multipart request specification:
https://github.com/jaydenseric/graphql-multipart-request-spec
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from django.core.files import File

__all__ = [
    "extract_files",
    "place_files",
]

from django.http import HttpResponseBadRequest
from graphene_django.views import HttpError


def extract_files(variables: dict[str, Any] | list[Any], *, prefix: str = "") -> dict[File, list[str]]:
    """
    Extract Django File objects paths in the given variables. Replace the file objects with None values.

    >>> file_1 = File(name="test_file_1.png")
    >>> file_2 = File(name="test_file_2.png")
    >>>
    >>> variables = {
    ...     "image": file_1,
    ...     "foo": [file_1, file_2],
    ...     "bar": {"one": file_2, "two": file_1},
    ... }
    ...
    >>> files = extract_files(variables, prefix="variables")
    >>> files
    {
        <File: test_file_1.png>: ["variables.image", "variables.foo.0", "variables.bar.two"],
        <File: test_file_2.png>: ["variables.foo.1", "variables.bar.one"],
    }
    >>> variables
    {
        "image": None,
        "foo": [None, None],
        "bar": {"one": None, "two": None}
    }
    """
    prefix = f"{prefix}." if prefix else prefix
    files: dict[File, list[str]] = defaultdict(list)
    iterable = enumerate(variables) if isinstance(variables, list) else variables.items()

    for key, value in iterable:
        if isinstance(value, File):
            variables[key] = None
            files[value].append(f"{prefix}{key}")

        if isinstance(value, (dict, list)):
            for sub_filename, sub_value in extract_files(value, prefix=f"{prefix}{key}").items():
                files[sub_filename] += sub_value

    return files


def place_files(operations: dict[str, Any], files_map: dict[str, list[str]], files: dict[str, File]) -> None:
    """
    Place files in the given operations using the files map.

    >>> file_1 = File(name="test_file_1.png")
    >>> file_2 = File(name="test_file_2.png")
    >>>
    >>> operations = {
    ...     "image": None,
    ...     "foo": [None, None],
    ...     "bar": {"one": None, "two": None},
    ... }
    ...
    >>> files_map = {
    ...     "0": ["image", "foo.0", "bar.two"]
    ...     "1": ["foo.1", "bar.one"],
    ... }
    ...
    >>> files = {
    ...     "0": file_1,
    ...     "1": file_2,
    ... }
    ...
    >>> place_files(operations, files_map, files)
    >>> operations
    {
        "image": file_1,
        "foo": [file_1, file_2],
        "bar": {"one": file_2, "two": file_1},
    }
    """
    for key, values in files_map.items():
        for value in values:
            path: list[str] = value.split(".")
            file: File = files.get(key)
            if file is None:  # pragma: no cover
                msg = f"File for path '{value}' not found in request files."
                raise HttpError(HttpResponseBadRequest(msg))

            _place_file(file, path, operations)


def _place_file(file: File, path: list[str], operations: dict[str, Any] | list[Any]) -> None:
    """Handle placing a single file to a single path in the `operations` object."""
    key: str | int = int(path[0]) if isinstance(operations, list) else path[0]

    try:
        ops: Any = operations[key]
    except (KeyError, IndexError, TypeError) as error:  # pragma: no cover
        msg = "File map does not lead to a null value."
        raise HttpError(HttpResponseBadRequest(msg)) from error

    path_left = path[1:]

    if path_left:
        return _place_file(file, path_left, ops)

    if ops is not None:  # pragma: no cover
        msg = "File map does not lead to a null value."
        raise HttpError(HttpResponseBadRequest(msg))

    operations[key] = file
    return None
