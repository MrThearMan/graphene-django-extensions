from rest_framework.exceptions import ErrorDetail

from graphene_django_extensions.errors import flatten_errors, get_constraint_message, to_field_errors


def test_get_constraint_message__check_postgres():
    msg = 'new row for relation "app_example" violates check constraint "check_example"'
    assert get_constraint_message(msg) == "Example constraint violation message."


def test_get_constraint_message__check_postgres__unknown_constraint():
    msg = 'new row for relation "app_example" violates check constraint "foo"'
    assert get_constraint_message(msg) == msg


def test_get_constraint_message__unique_postgres():
    msg = 'duplicate key value violates unique constraint "unique_name"'
    assert get_constraint_message(msg) == "Example unique violation message."


def test_get_constraint_message__unique_postgres__unknown_constraint():
    msg = 'duplicate key value violates unique constraint "foo"'
    assert get_constraint_message(msg) == msg


def test_get_constraint_message__check_sqlite():
    msg = "CHECK constraint failed: check_example"
    assert get_constraint_message(msg) == "Example constraint violation message."


def test_get_constraint_message__check_sqlite__unknown_constraint():
    msg = "CHECK constraint failed: foo"
    assert get_constraint_message(msg) == msg


def test_get_constraint_message__unique_sqlite():
    msg = "UNIQUE constraint failed: app_example.name, app_example.number"
    assert get_constraint_message(msg) == "Example unique violation message."


def test_get_constraint_message__unique_sqlite__unknown_fields():
    msg = "UNIQUE constraint failed: app_example.foo, app_example.bar"
    assert get_constraint_message(msg) == msg


def test_get_constraint_message__unknown_message():
    msg = "Unknown message."
    assert get_constraint_message(msg) == msg


def test_flatten_errors():
    errors = {"billing_address": {"city": ["msg1"], "post_code": ["msg2"]}}
    flattened = flatten_errors(errors)
    assert flattened == {"billing_address.city": ["msg1"], "billing_address.post_code": ["msg2"]}


def test_to_field_errors():
    data = {
        "city": [
            ErrorDetail(string="msg1", code="foo"),
            ErrorDetail(string="msg2", code="bar"),
        ],
        "post_code": ["msg3"],
    }

    assert to_field_errors(data) == [
        {"field": "city", "message": "msg1", "code": "foo"},
        {"field": "city", "message": "msg2", "code": "bar"},
        {"field": "post_code", "message": "msg3", "code": ""},
    ]
