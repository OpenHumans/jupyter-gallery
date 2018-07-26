import markdown as markdown_library
from django import template
from django.utils.safestring import mark_safe
from django.template.defaultfilters import stringfilter

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


@register.filter
@stringfilter
def upto(value, delimiter=None):
    return value.split(delimiter)[0]


upto.is_safe = True
