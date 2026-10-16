import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

pytestmark = [
    pytest.mark.django_db,
]

QUERY = "mutation ($input: ImageMutationInput!) { imageMutation(input: $input) { name success } }"


def upload(data: dict) -> dict:
    image = SimpleUploadedFile(name="image.png", content=b"content", content_type="image/png")
    response = Client().post("/graphql/", data={**data, "0": image})
    assert response.status_code == 400
    return response.json()


def error_message(content: dict) -> str:
    return content["errors"][0]["message"]


def test_file_upload__operations_missing():
    content = upload({"map": json.dumps({"0": ["variables.input.image"]})})
    assert error_message(content) == "File upload must contain an `operations` value."


def test_file_upload__operations_not_json():
    content = upload({"operations": "{", "map": json.dumps({"0": ["variables.input.image"]})})
    assert error_message(content) == "The `operations` value must be a JSON object."


def test_file_upload__operations_not_mapping():
    content = upload({"operations": json.dumps([]), "map": json.dumps({"0": ["variables.input.image"]})})
    assert error_message(content) == "The `operations` value is not a mapping."


def operations() -> str:
    return json.dumps({"query": QUERY, "variables": {"input": {"image": None}}})


def test_file_upload__map_missing():
    content = upload({"operations": operations()})
    assert error_message(content) == "File upload must contain an `map` value."


def test_file_upload__map_not_json():
    content = upload({"operations": operations(), "map": "{"})
    assert error_message(content) == "The `map` value must be a JSON object."


def test_file_upload__map_not_mapping():
    content = upload({"operations": operations(), "map": json.dumps([])})
    assert error_message(content) == "The `map` value is not a mapping."


@pytest.mark.parametrize("value", ["variables.input.image", [1]], ids=["not list", "not strings"])
def test_file_upload__map_values_not_list_of_strings(value):
    content = upload({"operations": operations(), "map": json.dumps({"0": value})})
    assert error_message(content) == "The `map` value is not a mapping from string to list of strings."


def test_file_upload__file_missing():
    content = upload({"operations": operations(), "map": json.dumps({"1": ["variables.input.image"]})})
    assert error_message(content) == "File for path 'variables.input.image' not found in request files."


def test_file_upload__path_does_not_exist():
    content = upload({"operations": operations(), "map": json.dumps({"0": ["variables.input.foo.bar"]})})
    assert error_message(content) == "File map does not lead to a null value."


def test_file_upload__path_not_null():
    data = json.dumps({"query": QUERY, "variables": {"input": {"image": "foo"}}})
    content = upload({"operations": data, "map": json.dumps({"0": ["variables.input.image"]})})
    assert error_message(content) == "File map does not lead to a null value."


def test_multipart_without_files():
    # Multipart requests without files are not file uploads, so they are parsed as regular GraphQL requests.
    response = Client().post("/graphql/", data={"query": "query { __typename }"})
    assert response.status_code == 200
    assert response.json() == {"data": {"__typename": "Query"}}
