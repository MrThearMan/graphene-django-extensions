import pytest

from example_project.app.models import Example

pytestmark = [
    pytest.mark.django_db,
]


def test_query_counter(query_counter):
    with query_counter() as results:
        Example.objects.count()

    assert len(results.queries) == 1
