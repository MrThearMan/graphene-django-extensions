from django.conf import settings
from django.urls import include, path
from graphene_django.views import GraphQLView

urlpatterns = [
    path("graphql/", GraphQLView.as_view(graphiql=True)),
]

if "debug_toolbar" in settings.INSTALLED_APPS:
    urlpatterns.append(path("__debug__/", include("debug_toolbar.urls")))
