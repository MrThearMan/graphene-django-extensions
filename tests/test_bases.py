from unittest.mock import Mock

import graphene
import pytest
from graphene_django.registry import get_global_registry
from rest_framework import serializers
from rest_framework.exceptions import ValidationError as SerializerValidationError

from example_project.app.forms import ExampleForm, ExampleInputForm, ExampleOutputForm
from example_project.app.models import Example, ForwardOneToOne
from example_project.app.mutations import ExampleUpdateMutation
from example_project.app.serializers import (
    ExampleCustomInputSerializer,
    ExampleCustomOutputSerializer,
    ExampleSerializer,
)
from graphene_django_extensions import CreateMutation, DeleteMutation, DjangoNode
from graphene_django_extensions.bases import DjangoMutation
from graphene_django_extensions.errors import GDXWarning
from graphene_django_extensions.options import DjangoNodeOptions
from tests.factories import ExampleFactory


@pytest.fixture
def isolated_registry(monkeypatch):
    """Let tests register object types without replacing the ones the example project uses."""
    registry = get_global_registry()
    monkeypatch.setattr(registry, "_registry", dict(registry._registry))
    return registry


# DjangoNode


def test_node__model_required():
    with pytest.raises(ValueError, match=r"`Meta.model` is required."):

        class Node(DjangoNode):
            class Meta:
                fields = ["pk"]


def test_node__model_must_be_a_model_class():
    with pytest.raises(TypeError, match=r"`Meta.model` needs to be a Model-class, received: `<class 'str'>`."):

        class Node(DjangoNode):
            class Meta:
                model = str
                fields = ["pk"]


def test_node__fields_required():
    with pytest.raises(ValueError, match=r"`Meta.fields` is required."):

        class Node(DjangoNode):
            class Meta:
                model = Example


def test_node__fields_must_be_a_sequence():
    with pytest.raises(TypeError, match=r"`Meta.fields` is should be a Sequence of field names or `__all__`"):

        class Node(DjangoNode):
            class Meta:
                model = Example
                fields = {"pk"}


def test_node__restricted_field_not_in_fields():
    with pytest.raises(ValueError, match=r"Field `name` not in `Meta.fields`."):

        class Node(DjangoNode):
            class Meta:
                model = Example
                fields = ["pk"]
                restricted_fields = {"name": lambda user: user.is_superuser}


def test_node__restricted_field__uses_existing_resolver():
    class Node(DjangoNode):
        class Meta:
            model = Example
            fields = ["pk", "name"]
            restricted_fields = {"name": lambda user: True}
            skip_registry = True

        @staticmethod
        def resolve_name(root: Example, info) -> str:
            return root.name.upper()

    root = Example(name="foo")
    assert Node.resolve_name(root, Mock()) == "FOO"


def test_node__custom_options(isolated_registry):
    class CustomNodeOptions(DjangoNodeOptions):
        extra: str = ""

    class CustomNode(DjangoNode):
        class Meta:
            abstract = True

        @classmethod
        def __init_subclass_with_meta__(cls, extra: str = "", **options):
            _meta = CustomNodeOptions(cls)
            _meta.extra = extra
            super().__init_subclass_with_meta__(_meta=_meta, **options)

    with pytest.warns(GDXWarning):

        class Node(CustomNode):
            class Meta:
                model = Example
                fields = ["pk", "name"]
                extra = "foo"

    assert isinstance(Node._meta, CustomNodeOptions)
    assert Node._meta.extra == "foo"


def test_node__skip_registry():
    registry = get_global_registry()
    existing = registry.get_type_for_model(Example)

    class Node(DjangoNode):
        class Meta:
            model = Example
            fields = ["pk", "name"]
            skip_registry = True

    assert registry.get_type_for_model(Example) is existing


def test_node__translation_fields__uses_existing_resolver(settings):
    settings.GRAPHENE_DJANGO_EXTENSIONS = {
        **settings.GRAPHENE_DJANGO_EXTENSIONS,
        "EXPERIMENTAL_TRANSLATION_FIELDS": True,
    }

    class NodeWithResolver(DjangoNode):
        class Meta:
            model = Example
            fields = ["pk", "name"]
            skip_registry = True

        @staticmethod
        def resolve_name(root: Example, info) -> str:
            return root.name.upper()

    assert NodeWithResolver.resolve_name(Example(name="foo"), Mock()) == "FOO"
    assert "name_translations" in NodeWithResolver._meta.fields


def test_node__model_already_registered__overrides_allowed(isolated_registry):
    with pytest.warns(GDXWarning, match=r"is already registered"):

        class Node(DjangoNode):
            class Meta:
                model = Example
                fields = ["pk", "name"]

    assert isolated_registry.get_type_for_model(Example) is Node


def test_node__model_already_registered__overrides_not_allowed(settings, isolated_registry):
    settings.GRAPHENE_DJANGO_EXTENSIONS = {
        **settings.GRAPHENE_DJANGO_EXTENSIONS,
        "ALLOW_MODEL_OBJECT_TYPE_REGISTRY_OVERRIDES": False,
    }

    with pytest.raises(LookupError, match=r"you should either use the existing object type or use proxy models"):

        class Node(DjangoNode):
            class Meta:
                model = Example
                fields = ["pk", "name"]


# DjangoMutation


def test_mutation__create__serializer_or_form_required():
    msg = r"`Meta.serializer_class` or `Meta.form_class` is required for create and update mutations."
    with pytest.raises(ValueError, match=msg):

        class Mutation(CreateMutation):
            class Meta:
                pass


def test_mutation__create__serializer_must_be_model_serializer():
    with pytest.raises(TypeError, match=r"`Meta.serializer_class` needs to be a ModelSerializer subclass."):

        class Mutation(CreateMutation):
            class Meta:
                serializer_class = ExampleCustomInputSerializer


def test_mutation__create__output_serializer_must_be_model_serializer():
    with pytest.raises(TypeError, match=r"`Meta.output_serializer_class` needs to be a ModelSerializer subclass."):

        class Mutation(CreateMutation):
            class Meta:
                serializer_class = ExampleSerializer
                output_serializer_class = ExampleCustomOutputSerializer


def test_mutation__create__nested_serializer_model_not_registered(isolated_registry):
    del isolated_registry._registry[ForwardOneToOne]

    with pytest.raises(LookupError, match=r"Could not find a ObjectType for model: `ForwardOneToOne`."):

        class Mutation(CreateMutation):
            class Meta:
                serializer_class = ExampleSerializer


def test_mutation__create__form_must_be_model_form():
    with pytest.raises(TypeError, match=r"`Meta.form_class` needs to be a ModelForm subclass."):

        class Mutation(CreateMutation):
            class Meta:
                form_class = ExampleInputForm


def test_mutation__create__output_form_must_be_model_form():
    with pytest.raises(TypeError, match=r"`Meta.output_form_class` needs to be a ModelForm subclass."):

        class Mutation(CreateMutation):
            class Meta:
                form_class = ExampleForm
                output_form_class = ExampleOutputForm


def test_mutation__delete__model_required():
    with pytest.raises(ValueError, match=r"`Meta.model` is required."):

        class Mutation(DeleteMutation):
            class Meta:
                pass


@pytest.mark.django_db
def test_mutation__delete__custom_lookup_field():
    class Mutation(DeleteMutation):
        class Meta:
            model = Example
            lookup_field = "email"

    example = ExampleFactory.create(email="foo@email.com")
    info = Mock()

    result = Mutation.delete(info, {"email": "foo@email.com"})

    assert result.deleted is True
    assert not Example.objects.filter(pk=example.pk).exists()


def test_mutation__update__lookup_field_missing():
    with pytest.raises(SerializerValidationError) as error:
        ExampleUpdateMutation.get_instance({})

    assert error.value.detail == {"pk": "This field is required."}


def test_mutation__custom__not_implemented():
    with pytest.raises(NotImplementedError, match=r"Custom model operation not defined for 'DjangoMutation'"):
        DjangoMutation.custom_mutation(Mock(), {})


def test_mutation__custom__custom_mutation_must_be_overridden():
    with pytest.raises(ValueError, match=r"`custom_mutation` must be overridden in subclasses for custom mutations"):

        class Mutation(DjangoMutation):
            class Meta:
                serializer_class = ExampleCustomInputSerializer


def test_mutation__custom__serializer_or_form_required():
    with pytest.raises(ValueError, match=r"`Meta.serializer_class` or `Meta.form_class` is required for custom"):

        class Mutation(DjangoMutation):
            class Meta:
                pass

            @classmethod
            def custom_mutation(cls, info, input_data):
                return cls()


def test_mutation__custom__serializer_must_be_serializer():
    with pytest.raises(TypeError, match=r"`Meta.serializer_class` needs to be a Serializer subclass."):

        class Mutation(DjangoMutation):
            class Meta:
                serializer_class = ExampleInputForm

            @classmethod
            def custom_mutation(cls, info, input_data):
                return cls()


def test_mutation__custom__output_serializer_must_be_serializer():
    with pytest.raises(TypeError, match=r"`Meta.output_serializer_class` needs to be a Serializer subclass."):

        class Mutation(DjangoMutation):
            class Meta:
                serializer_class = ExampleCustomInputSerializer
                output_serializer_class = ExampleOutputForm

            @classmethod
            def custom_mutation(cls, info, input_data):
                return cls()


def test_mutation__custom__input_class_must_be_input_object_type():
    with pytest.raises(TypeError, match=r"`input_class` must be a subclass of `graphene.InputObjectType`."):

        class Mutation(DjangoMutation):
            class Meta:
                serializer_class = ExampleCustomInputSerializer
                input_class = graphene.ObjectType

            @classmethod
            def custom_mutation(cls, info, input_data):
                return cls()


def test_mutation__custom__serializer_output():
    class OutputSerializer(serializers.Serializer):
        name = serializers.CharField()
        password = serializers.CharField(write_only=True)
        greeting = serializers.SerializerMethodField()

        def get_greeting(self, obj: Example) -> str:
            return f"Hello {obj.name}!"

    class Mutation(DjangoMutation):
        class Meta:
            serializer_class = ExampleCustomInputSerializer
            output_serializer_class = OutputSerializer

        @classmethod
        def custom_mutation(cls, info, input_data):
            return cls()

    output = Mutation.get_serializer_output(Example(name="foo"))

    assert output == {"name": "foo", "greeting": "Hello foo!"}
