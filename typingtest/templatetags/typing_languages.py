from django import template

from typingtest.languages import LANGUAGES

register = template.Library()


@register.simple_tag
def typing_languages():
    """The language list for shared templates, such as the site menu."""
    return LANGUAGES
