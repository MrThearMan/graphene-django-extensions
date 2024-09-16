from modeltranslation.translator import TranslationOptions, translator

from .models import Example


class ExampleTranslationOptions(TranslationOptions):
    fields = ["name"]


translator.register(Example, ExampleTranslationOptions)
