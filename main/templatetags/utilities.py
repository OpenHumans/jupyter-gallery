import markdown as markdown_library
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def markdown(value):
    """
    Translate markdown to a safe subset of HTML.
    """
    md_text = markdown_library.markdown(value)
    return mark_safe(md_text)


@register.simple_tag
def concatenate(*args):
    args = [str(arg) for arg in args]
    return "_".join(args)
