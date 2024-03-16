import json
from typing import TYPE_CHECKING

from django.http import HttpRequest, HttpResponseBadRequest
from graphene_django.views import GraphQLView, HttpError

from .files import place_files
from .typing import Any

if TYPE_CHECKING:
    from django.core.files import File

__all__ = [
    "FileUploadGraphQLView",
]


class FileUploadGraphQLView(GraphQLView):
    def parse_body(self, request: HttpRequest) -> dict[str, Any]:
        if self.is_file_upload(request):
            return self.parse_file_uploads(request)
        return super().parse_body(request)

    def is_file_upload(self, request: HttpRequest) -> bool:
        content_type = self.get_content_type(request)
        return content_type == "multipart/form-data" and request.FILES

    def parse_file_uploads(self, request: HttpRequest) -> dict[str, Any]:
        operations = self.get_operations(request)
        files_map = self.get_map(request)
        files: dict[str, File] = request.FILES  # type: ignore[assignment]
        place_files(operations, files_map, files)
        return operations

    @staticmethod
    def get_operations(request: HttpRequest) -> dict[str, Any]:  # pragma: no cover
        operations_str: str | None = request.POST.get("operations")
        if not isinstance(operations_str, str):
            msg = "File upload must contain an `operations` value."
            raise HttpError(HttpResponseBadRequest(msg))

        try:
            operations: dict[str, Any] = json.loads(operations_str)
        except json.JSONDecodeError as error:
            msg = "The `operations` value must be a JSON object."
            raise HttpError(HttpResponseBadRequest(msg)) from error

        if not isinstance(operations, dict):
            msg = "The `operations` value is not a mapping."
            raise HttpError(HttpResponseBadRequest(msg))

        return operations

    @staticmethod
    def get_map(request: HttpRequest) -> dict[str, list[str]]:  # pragma: no cover
        files_map_str: str | None = request.POST.get("map")
        if not isinstance(files_map_str, str):
            msg = "File upload must contain an `map` value."
            raise HttpError(HttpResponseBadRequest(msg))

        try:
            files_map: dict[str, list[str]] = json.loads(files_map_str)
        except json.JSONDecodeError as error:
            msg = "The `map` value must be a JSON object."
            raise HttpError(HttpResponseBadRequest(msg)) from error

        if not isinstance(files_map, dict):
            msg = "The `map` value is not a mapping."
            raise HttpError(HttpResponseBadRequest(msg))

        for value in files_map.values():
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                msg = "The `map` value is not a mapping from string to list of strings."
                raise HttpError(HttpResponseBadRequest(msg))

        return files_map
