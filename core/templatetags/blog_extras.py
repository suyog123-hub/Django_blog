"""Custom template tags and filters for the blogging platform."""

from django import template
from django.urls import resolve, reverse
from django.utils import timezone
from django.utils.safestring import mark_safe

from ..services import add_heading_ids, build_toc, render_markdown

register = template.Library()


@register.filter(name="md")
def md(value):
    """Render a string of Markdown as safe HTML."""
    if not value:
        return ""
    return mark_safe(add_heading_ids(render_markdown(value)))


@register.filter(name="toc")
def toc(value):
    """Return the table-of-contents structure for a Markdown string."""
    return build_toc(add_heading_ids(render_markdown(value)))


@register.simple_tag
def reading_time(text):
    """Estimate reading time for *text* in whole minutes."""
    from ..services import estimate_reading_time

    return estimate_reading_time(text)


@register.filter(name="timesince_short")
def timesince_short(value):
    """Compact relative date, e.g. '3d' / '2h' / '5m'."""
    if not value:
        return ""
    delta = timezone.now() - value
    seconds = delta.total_seconds()
    if seconds < 60:
        return "just now"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes}m"
    hours = int(minutes // 60)
    if hours < 24:
        return f"{hours}h"
    days = int(hours // 24)
    if days < 30:
        return f"{days}d"
    months = int(days // 30)
    if months < 12:
        return f"{months}mo"
    return f"{int(months // 12)}y"


@register.filter(name="pluralize_word")
def pluralize_word(count, singular):
    """Return the correctly pluralised form of *singular* for *count*."""
    if count == 1:
        return singular
    return singular + "s"


@register.simple_tag
def active_nav(request, *names):
    """Return ``active`` when the current URL name is one of *names*."""
    try:
        resolved = resolve(request.path).url_name
    except Exception:
        resolved = None
    return "active" if resolved in names else ""


@register.simple_tag
def build_url(view_name, **kwargs):
    try:
        return reverse(view_name, kwargs=kwargs)
    except Exception:
        return "#"
