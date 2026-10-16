import warnings
from importlib import reload

import pytest
from graphene_django import settings as graphene_django_settings
from graphene_django import views

from example_project.app import nodes, schema
from graphene_django_extensions.errors import GDXWarning


def reload_schema() -> None:
    # Reloading the nodes registers the same object types again, which is expected here.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=GDXWarning)
        reload(nodes)
    reload(schema)
    # Point the views to the reloaded graphene settings, which know about the new schema.
    # Reloading the views module would replace its exception classes, which other modules have imported.
    views.graphene_settings = graphene_django_settings.graphene_settings


@pytest.fixture
def experimental_translation_fields(settings, request):
    param = getattr(request, "param", "types")

    old_settings = settings.GRAPHENE_DJANGO_EXTENSIONS.copy()
    try:
        settings.GRAPHENE_DJANGO_EXTENSIONS = {
            **old_settings,
            "EXPERIMENTAL_TRANSLATION_FIELDS": True,
            "EXPERIMENTAL_TRANSLATION_FIELDS_KIND": param,
        }
        # Reload graphene settings so that views know about the new schema.
        settings.GRAPHENE = settings.GRAPHENE

        # Recreate nodes, schema and views (new schema added).
        reload_schema()
        yield

    finally:
        # Restore settings and schema.
        settings.GRAPHENE_DJANGO_EXTENSIONS = old_settings
        settings.GRAPHENE = settings.GRAPHENE
        reload_schema()
