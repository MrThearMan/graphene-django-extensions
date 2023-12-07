from graphene_django_extensions.errors import flatten_errors, get_constraint_message


def test_get_constraint_message__check_postgres():
    msg = 'new row for relation "example_example" violates check constraint "check_example"'
    assert get_constraint_message(msg) == "Example constraint violation message."


def test_get_constraint_message__check_postgres__unknown_constraint():
    msg = 'new row for relation "example_example" violates check constraint "foo"'
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
    msg = "UNIQUE constraint failed: example_example.name, example_example.number"
    assert get_constraint_message(msg) == "Example unique violation message."


def test_get_constraint_message__unique_sqlite__unknown_fields():
    msg = "UNIQUE constraint failed: example_example.foo, example_example.bar"
    assert get_constraint_message(msg) == msg


def test_get_constraint_message__unknown_message():
    msg = "Unknown message."
    assert get_constraint_message(msg) == msg


def test_flatten_errors():
    errors = {"billing_address": {"city": ["msg1"], "post_code": ["msg2"]}}
    flattened = flatten_errors(errors)
    assert flattened == {"billing_address.city": ["msg1"], "billing_address.post_code": ["msg2"]}
