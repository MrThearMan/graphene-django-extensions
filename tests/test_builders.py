import re
from enum import Enum

import pytest

from graphene_django_extensions.testing import build_mutation, build_query


class MyEnum(Enum):
    ONE = "ONE"
    TWO = "TWO"


def test_query_builder__default():
    assert build_query("example") == "query { example { pk } }"


def test_query_builder__fields():
    assert build_query("example", fields="foo bar fizz { buzz }") == "query { example { foo bar fizz { buzz } } }"


def test_query_builder__filters__single():
    assert build_query("example", foo="bar") == 'query { example(foo: "bar") { pk } }'


def test_query_builder__filters__multiple():
    assert build_query("example", foo="bar", baz=1) == 'query { example(foo: "bar", baz: 1) { pk } }'


def test_query_builder__filters__has_lookups():
    assert build_query("example", pk__gte=1) == "query { example(pk_Gte: 1) { pk } }"


def test_query_builder__filters__enums():
    assert build_query("example", pk=MyEnum.ONE) == "query { example(pk: ONE) { pk } }"


def test_query_builder__filters__enums_list():
    assert build_query("example", pk=[MyEnum.ONE, MyEnum.TWO]) == "query { example(pk: [ONE, TWO]) { pk } }"


def test_query_builder__field_filters__single():
    assert build_query("example", pk__foo="bar") == 'query { example { pk(foo: "bar") } }'


def test_query_builder__field_filters__multiple():
    assert build_query("example", pk__foo="bar", pk__bar=1) == 'query { example { pk(foo: "bar", bar: 1) } }'


def test_query_builder__field_filters__nested():
    assert build_query("example", fields="one { two }", one__foo="bar", one__two__bar=1) == (
        'query { example { one(foo: "bar") { two(bar: 1) } } }'
    )


def test_query_builder__field_filters__has_lookups():
    assert build_query("example", pk__foo__contains="bar") == 'query { example { pk(foo_Contains: "bar") } }'


def test_query_builder__field_filters__enums():
    assert build_query("example", pk__foo=MyEnum.TWO) == "query { example { pk(foo: TWO) } }"


def test_query_builder__field_filters__enums_list():
    assert build_query("example", pk__foo=[MyEnum.ONE, MyEnum.TWO]) == "query { example { pk(foo: [ONE, TWO]) } }"


@pytest.mark.parametrize(
    ["fields", "error"],
    [
        ("pk{foo}", "pk{foo}"),
        ("pk{foo }", "pk{foo"),
        ("pk{ foo}", "pk{"),
        ("pk {foo}", "{foo}"),
        ("pk {foo }", "{foo"),
        ("pk { foo}", "foo}"),
    ],
)
def test_query_builder__field_filters__no_spaces_between_braces(fields, error):
    error = "Should include a space before or after the '{' and/or '}' characters: " + f"'{error}'"
    with pytest.raises(RuntimeError, match=re.escape(error)):
        build_query("example", fields=fields, pk__foo="bar")


def test_query_builder__field_filters__field_not_selected():
    error = "Field filters '(bar: 1)' defined for field 'foo' but not in selected fields: 'pk'"
    with pytest.raises(RuntimeError, match=re.escape(error)):
        build_query("example", foo__bar=1)


def test_mutation_builder__default():
    assert build_mutation("createExample", "ExampleCreateMutation") == (
        "mutation createExample($input: ExampleCreateMutationInput!) "
        "{ createExample(input: $input) { pk errors { messages field } } }"
    )


def test_mutation_builder__fields():
    assert build_mutation("deleteExample", "ExampleDeleteMutation", fields="pk deleted") == (
        "mutation deleteExample($input: ExampleDeleteMutationInput!) { deleteExample(input: $input) { pk deleted } }"
    )
