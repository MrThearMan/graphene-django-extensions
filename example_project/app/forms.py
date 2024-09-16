from django.forms import CharField, Form, IntegerField, ModelForm

from example_project.app.models import Example


class ExampleForm(ModelForm):
    class Meta:
        model = Example
        fields = [
            "name",
            "number",
            "email",
            "example_state",
            "duration",
            "forward_one_to_one_field",
            "forward_many_to_one_field",
        ]


class ExampleInputForm(Form):
    name = CharField(required=True)


class ExampleOutputForm(Form):
    pk = IntegerField()
