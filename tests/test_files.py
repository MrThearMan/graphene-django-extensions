import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from graphene_django_extensions.files import extract_files, place_files

pytestmark = [
    pytest.mark.django_db,
]


def test_extract_files():
    file_1 = SimpleUploadedFile(name="test_file_1.png", content=b"content", content_type="image/png")
    file_2 = SimpleUploadedFile(name="test_file_2.png", content=b"content", content_type="image/png")

    variables = {
        "image": file_1,
        "foo": [file_1, 5, file_2],
        "bar": {"one": file_2, "two": file_1, "three": 1},
        "fizz": "buzz",
        "1": None,
        "2": type(None),
    }

    files = extract_files(variables, prefix="variables")

    assert files == {
        file_1: ["variables.image", "variables.foo.0", "variables.bar.two"],
        file_2: ["variables.foo.2", "variables.bar.one"],
    }
    assert variables == {
        "image": None,
        "foo": [None, 5, None],
        "bar": {"one": None, "two": None, "three": 1},
        "fizz": "buzz",
        "1": None,
        "2": type(None),
    }


def test_place_files():
    file_1 = SimpleUploadedFile(name="test_file_1.png", content=b"content", content_type="image/png")
    file_2 = SimpleUploadedFile(name="test_file_2.png", content=b"content", content_type="image/png")

    operations = {
        "image": None,
        "foo": [None, 5, None],
        "bar": {"one": None, "two": None, "three": 1},
        "fizz": "buzz",
        "1": None,
        "2": type(None),
    }
    files_map = {
        "0": ["image", "foo.0", "bar.two"],
        "1": ["foo.2", "bar.one"],
    }
    files = {
        "0": file_1,
        "1": file_2,
    }

    place_files(operations, files_map, files)

    assert operations == {
        "image": file_1,
        "foo": [file_1, 5, file_2],
        "bar": {"one": file_2, "two": file_1, "three": 1},
        "fizz": "buzz",
        "1": None,
        "2": type(None),
    }
