from importlib import reload

import pytest
from graphene_django import views

from tests.example import nodes, schema


@pytest.fixture()
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

        # Reload these modules:
        reload(nodes)  # Recreate nodes
        reload(schema)  # Recreate schema
        reload(views)  # Recreate views (new schema added)
        yield

    finally:
        # Restore settings and schema.
        settings.GRAPHENE_DJANGO_EXTENSIONS = old_settings
        settings.GRAPHENE = settings.GRAPHENE
        reload(nodes)
        reload(schema)
        reload(views)
