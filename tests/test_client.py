import pytest

from graphene_django_extensions.testing.client import GQLResponse
from graphene_django_extensions.testing.utils import QueryData


class MockResponse:
    def __init__(self, content):
        self.content = content

    def json(self):
        return self.content


def make_response(content, queries=None) -> GQLResponse:
    return GQLResponse(MockResponse(content), QueryData(queries=queries or []))


def test_gql_response__str_and_repr():
    response = make_response({"data": {"foo": {"name": "bar"}}})

    assert str(response) == '{\n  "data": {\n    "foo": {\n      "name": "bar"\n    }\n  }\n}'
    assert repr(response) == "{'data': {'foo': {'name': 'bar'}}}"


def test_gql_response__getitem():
    response = make_response({"data": {"foo": {"name": "bar"}}})

    assert response["foo"] == {"name": "bar"}


def test_gql_response__first_query_object():
    response = make_response({"data": {"foo": {"name": "bar"}}})

    assert response.first_query_object == {"name": "bar"}


def test_gql_response__first_query_object__no_data():
    response = make_response({"data": None})

    with pytest.raises(pytest.fail.Exception, match="No query object not found in response content"):
        response.first_query_object  # noqa: B018


def test_gql_response__edges_and_node():
    response = make_response({"data": {"foo": {"edges": [{"node": {"name": "bar"}}]}}})

    assert response.edges == [{"node": {"name": "bar"}}]
    assert len(response) == 1
    assert response.node(0) == {"name": "bar"}


def test_gql_response__edges__not_a_connection():
    response = make_response({"data": {"foo": {"name": "bar"}}})

    with pytest.raises(pytest.fail.Exception, match="Edges not found in response content"):
        response.edges  # noqa: B018


def test_gql_response__edges__null_query_object():
    response = make_response({"data": {"foo": None}})

    with pytest.raises(pytest.fail.Exception, match="Edges not found in response content"):
        response.edges  # noqa: B018


def test_gql_response__node__index_out_of_range():
    response = make_response({"data": {"foo": {"edges": []}}})

    with pytest.raises(pytest.fail.Exception, match="Node 0 not found in response content"):
        response.node(0)


def test_gql_response__has_errors():
    assert make_response({"data": None, "errors": [{"message": "foo"}]}).has_errors is True
    assert make_response({"data": None, "errors": None}).has_errors is False
    assert make_response({"data": None}).has_errors is False


def test_gql_response__errors__missing():
    response = make_response({"data": {"foo": None}})

    with pytest.raises(pytest.fail.Exception, match="Errors not found in response content"):
        response.errors  # noqa: B018


def test_gql_response__error_message__by_index():
    response = make_response({"errors": [{"message": "foo"}, {"message": "bar"}]})

    assert response.error_message() == "foo"
    assert response.error_message(1) == "bar"


def test_gql_response__error_message__index_out_of_range():
    response = make_response({"errors": [{"message": "foo"}]})

    with pytest.raises(pytest.fail.Exception, match="Errors list doesn't have an index 1"):
        response.error_message(1)


def test_gql_response__error_message__by_index__no_message():
    response = make_response({"errors": [{"path": ["foo"]}]})

    with pytest.raises(pytest.fail.Exception, match="Field 'message' not found in error content"):
        response.error_message(0)


def test_gql_response__error_message__by_path():
    response = make_response({"errors": [{"message": "foo", "path": ["fizz", "buzz"]}]})

    assert response.error_message("buzz") == "foo"


def test_gql_response__error_message__by_path__not_found():
    response = make_response({"errors": [{"message": "foo", "path": ["fizz", "buzz"]}]})

    with pytest.raises(pytest.fail.Exception, match="Errors list doesn't have an error for field 'fizz'"):
        response.error_message("fizz")


def test_gql_response__error_message__by_path__no_path():
    response = make_response({"errors": [{"message": "foo"}]})

    with pytest.raises(pytest.fail.Exception, match="Field 'message' not found in error content"):
        response.error_message("fizz")


def test_gql_response__field_errors():
    errors = [{"field": "foo", "message": "bar", "code": "baz"}]
    response = make_response({"errors": [{"extensions": {"errors": errors}}, {"message": "no extensions"}]})

    assert response.field_errors == errors


def test_gql_response__field_errors__errors_null():
    response = make_response({"errors": None})

    with pytest.raises(pytest.fail.Exception, match="Field errors not found in response content"):
        response.field_errors  # noqa: B018


def test_gql_response__field_error_messages():
    errors = [
        {"field": "foo", "message": "bar", "code": "baz"},
        {"field": "other", "message": "one", "code": "two"},
        {"field": "foo", "message": "fizz", "code": ""},
    ]
    response = make_response({"errors": [{"extensions": {"errors": errors}}]})

    assert response.field_error_messages("foo") == ["bar", "fizz"]


def test_gql_response__field_error_messages__no_message():
    response = make_response({"errors": [{"extensions": {"errors": [{"field": "foo", "code": "baz"}]}}]})

    with pytest.raises(pytest.fail.Exception, match="Error message for field 'foo' not found in error"):
        response.field_error_messages("foo")


def test_gql_response__error_code__by_index():
    response = make_response({"errors": [{"message": "foo", "extensions": {"code": "bar"}}]})

    assert response.error_code() == "bar"


def test_gql_response__error_code__by_index__no_extensions():
    response = make_response({"errors": [{"message": "foo"}]})

    with pytest.raises(pytest.fail.Exception, match="Error code not found in error content"):
        response.error_code(0)


def test_gql_response__error_code__by_path():
    response = make_response({"errors": [{"extensions": {"code": "bar"}, "path": ["fizz", "buzz"]}]})

    assert response.error_code("buzz") == "bar"


def test_gql_response__error_code__by_path__not_found():
    response = make_response({"errors": [{"extensions": {"code": "bar"}, "path": ["fizz", "buzz"]}]})

    with pytest.raises(pytest.fail.Exception, match="Errors list doesn't have an error for field 'fizz'"):
        response.error_code("fizz")


def test_gql_response__error_code__by_path__no_extensions():
    response = make_response({"errors": [{"message": "foo", "path": ["fizz", "buzz"]}]})

    with pytest.raises(pytest.fail.Exception, match="Field 'extensions' not found in error content"):
        response.error_code("buzz")


def test_gql_response__field_error_codes():
    errors = [
        {"field": "foo", "message": "bar", "code": "baz"},
        {"field": "other", "message": "one", "code": "two"},
        {"field": "foo", "message": "fizz", "code": ""},
    ]
    response = make_response({"errors": [{"extensions": {"errors": errors}}]})

    assert response.field_error_codes("foo") == ["baz", ""]


def test_gql_response__field_error_codes__no_code():
    response = make_response({"errors": [{"extensions": {"errors": [{"field": "foo", "message": "bar"}]}}]})

    with pytest.raises(pytest.fail.Exception, match="Error code for field 'foo' not found in error"):
        response.field_error_codes("foo")


def test_gql_response__has_schema_errors():
    assert make_response({"errors": [{"message": "Variable '$input' got invalid value"}]}).has_schema_errors is True
    assert make_response({"errors": [{"message": "foo"}]}).has_schema_errors is False


def test_gql_response__assert_query_count():
    response = make_response({"data": None}, queries=["SELECT 1"])

    response.assert_query_count(1)

    with pytest.raises(pytest.fail.Exception, match="Expected 2 queries, got 1"):
        response.assert_query_count(2)


@pytest.mark.django_db
def test_graphql_client__operation_name(graphql):
    query = "query First { __typename } query Second { second: __typename }"

    response = graphql(query, operation_name="Second")

    assert response.has_errors is False
    assert response.json == {"data": {"second": "Query"}}
