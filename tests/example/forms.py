from django.forms import CharField, Form, IntegerField, ModelForm

from tests.example.models import Example


class ExampleForm(ModelForm):
    class Meta:
        model = Example
        fields = [
            "name",
            "number",
            "email",
            "example_state",
            "forward_one_to_one_field",
            "forward_many_to_one_field",
        ]


class ExampleInputForm(Form):
    name = CharField(required=True)


class ExampleOutputForm(Form):
    pk = IntegerField()
