from django.conf import settings
from django.urls import include, path

from graphene_django_extensions.views import FileUploadGraphQLView

urlpatterns = [
    path("graphql/", FileUploadGraphQLView.as_view(graphiql=True)),
    path("i18n/", include("django.conf.urls.i18n")),
]

if "debug_toolbar" in settings.INSTALLED_APPS:
    urlpatterns.append(path("__debug__/", include("debug_toolbar.urls")))
