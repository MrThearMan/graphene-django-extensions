from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.db import models

from .errors import GQLNotFoundError
from .settings import gdx_settings

if TYPE_CHECKING:
    from django.db.models import ForeignObjectRel
    from django.db.models.fields.related import RelatedField

    from .typing import Any, RelationType


__all__ = [
    "get_object_or_404",
    "get_model_lookup_field",
    "get_related_field_info",
]


def get_object_or_404(model_class: type[models.Model], **kwargs: Any) -> models.Model:
    try:
        return model_class._default_manager.get(**kwargs)
    except model_class.DoesNotExist as error:
        msg = f"`{model_class.__name__}` object matching query `{kwargs}` does not exist."
        raise GQLNotFoundError(msg, code=gdx_settings.NOT_FOUND_ERROR_CODE) from error


def get_model_lookup_field(model_class: type[models.Model], lookup_field: str | None = None) -> str:
    if lookup_field is None:
        # Use model primary key as lookup field.
        # This is usually the 'id' field, in which case we use 'pk' instead
        # to avoid collision with the 'id' field in GraphQL Relay nodes.
        lookup_field = model_class._meta.pk.name
        if lookup_field == "id":
            lookup_field = "pk"
    return lookup_field


@dataclass
class RelatedFieldInfo:
    """Information about a related field on a model."""

    name: str
    forward: bool
    relation: RelationType

    @property
    def one_to_one(self) -> bool:
        return self.relation == "one_to_one"

    @property
    def many_to_one(self) -> bool:
        return self.relation == "many_to_one"

    @property
    def one_to_many(self) -> bool:
        return self.relation == "one_to_many"

    @property
    def many_to_many(self) -> bool:
        return self.relation == "many_to_many"

    @property
    def reverse(self) -> bool:
        return not self.forward


def get_related_field_info(model: type[models.Model]) -> dict[str, RelatedFieldInfo]:
    """Map of all related fields on the given model to their related entity's field names."""
    mapping: dict[str, RelatedFieldInfo] = {}
    for field in model._meta.get_fields():
        if isinstance(field, (models.OneToOneRel, models.ManyToOneRel, models.ManyToManyRel)):
            name: str = field.get_accessor_name() or field.name
            mapping[name] = RelatedFieldInfo(
                name=field.remote_field.name,
                forward=False,
                relation=_get_relation_type(field),
            )

        if isinstance(field, (models.OneToOneField, models.ForeignKey, models.ManyToManyField)):
            value = field.remote_field.get_accessor_name() or field.name
            mapping[field.name] = RelatedFieldInfo(
                name=value,
                forward=True,
                relation=_get_relation_type(field),
            )
            continue

    return mapping


def _get_relation_type(field: ForeignObjectRel | RelatedField) -> RelationType:
    return (
        "one_to_one"
        if field.one_to_one
        else "many_to_one"
        if field.many_to_one
        else "one_to_many"
        if field.one_to_many
        else "many_to_many"
    )
