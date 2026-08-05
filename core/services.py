"""Business logic helpers shared by views.

Keeping logic here (rather than inside views) makes it reusable, testable
and keeps views thin.
"""

import hashlib
import re

import bleach
import markdown as markdown_lib
from django.db.models import Count, F, Q
from django.utils import timezone

from .models import Blog

# Bleach configuration used to sanitize user generated Markdown HTML.
BLEACH_ALLOWED_TAGS = list(bleach.sanitizer.ALLOWED_TAGS) + [
    "p", "h1", "h2", "h3", "h4", "h5", "h6",
    "img", "hr", "pre", "code", "br",
    "table", "thead", "tbody", "tr", "th", "td",
    "ul", "ol", "li", "blockquote", "strong", "em",
    "a", "span", "div", "figure", "figcaption",
    "del", "sup", "sub", "mark", "input", "details", "summary",
]
BLEACH_ALLOWED_ATTRS = {
    **bleach.sanitizer.ALLOWED_ATTRIBUTES,
    "*": ["class", "id", "title"],
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "width", "height"],
    "code": ["class"],
    "input": ["type", "checked", "disabled"],
}
BLEACH_ALLOWED_PROTOCOLS = bleach.sanitizer.ALLOWED_PROTOCOLS | {"data"}

HEADING_RE = re.compile(r"<h([1-6])[^>]*>(.*?)</h\1>", re.IGNORECASE)
STRIP_TAGS_RE = re.compile(r"<[^>]+>")


# ---------------------------------------------------------------------------
# Markdown rendering (safe by default)
# ---------------------------------------------------------------------------
def render_markdown(source, *, linkify=True):
    """Convert Markdown source to sanitized HTML.

    Uses ``bleach`` after rendering so untrusted content can't inject
    scripts (XSS protection).
    """
    if not source:
        return ""
    raw_html = markdown_lib.markdown(
        source,
        extensions=[
            "markdown.extensions.fenced_code",
            "markdown.extensions.tables",
            "markdown.extensions.toc",
            "markdown.extensions.nl2br",
            "markdown.extensions.sane_lists",
            "markdown.extensions.attr_list",
        ],
    )
    return bleach.clean(
        raw_html,
        tags=BLEACH_ALLOWED_TAGS,
        attributes=BLEACH_ALLOWED_ATTRS,
        protocols=BLEACH_ALLOWED_PROTOCOLS,
        strip=True,
    )


# ---------------------------------------------------------------------------
# Table of contents
# ---------------------------------------------------------------------------
def build_toc(rendered_html):
    """Extract ``(id, level, title)`` tuples from rendered heading HTML.

    Returns a structure the templates can render as a sticky TOC.
    """
    items = []
    for match in HEADING_RE.finditer(rendered_html or ""):
        level = int(match.group(1))
        title = STRIP_TAGS_RE.sub("", match.group(2)).strip()
        anchor = slugify_heading(title)
        items.append({"id": anchor, "level": level, "title": title})
    return items


def slugify_heading(text):
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
    return slug or "section"


def add_heading_ids(rendered_html):
    """Rewrite ``<hN>`` elements to include stable ``id`` anchors for the TOC."""
    def replace(match):
        level, inner = match.group(1), match.group(2)
        title = STRIP_TAGS_RE.sub("", inner).strip()
        anchor = slugify_heading(title)
        return f'<h{level} id="{anchor}">{inner}</h{level}>'

    return HEADING_RE.sub(replace, rendered_html)


# ---------------------------------------------------------------------------
# Reading time
# ---------------------------------------------------------------------------
def estimate_reading_time(text, words_per_minute=200):
    """Return a whole-minute estimate for *text*."""
    words = len((text or "").split())
    return max(1, round(words / words_per_minute))


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------
def related_posts(blog, limit=3):
    """Pick related posts: shared category first, then shared tags."""
    qs = (
        Blog.objects.published()
        .with_relations()
        .with_counts()
        .exclude(pk=blog.pk)
    )
    related = qs.filter(category=blog.category)[:limit]
    if len(related) < limit:
        tag_ids = list(blog.tags.values_list("id", flat=True))
        remaining = qs.exclude(pk__in=[b.pk for b in related]).filter(
            tags__id__in=tag_ids
        ).distinct()[: limit - len(related)]
        related = list(related) + list(remaining)
    if len(related) < limit:
        fallback = qs.exclude(pk__in=[b.pk for b in related])[: limit - len(related)]
        related = list(related) + list(fallback)
    return related


def popular_posts(limit=5):
    return (
        Blog.objects.published()
        .with_relations()
        .with_counts()
        .order_by("-view_count")
        [:limit]
    )


def trending_posts(limit=5, days=7):
    """Trending = most viewed within the last *days* days."""
    cutoff = timezone.now() - timezone.timedelta(days=days)
    return (
        Blog.objects.published()
        .filter(views__created_at__gte=cutoff)
        .annotate(views_in_window=Count("views", distinct=True))
        .order_by("-views_in_window", "-view_count")
        .with_relations()
        .with_counts()
        .distinct()[:limit]
    )


def recommended_for(user, limit=5):
    """Personalised picks based on categories/tags the user has read or liked."""
    if not (user and user.is_authenticated):
        return popular_posts(limit)
    liked_categories = Blog.objects.filter(
        likes=user, status=Blog.Status.PUBLISHED
    ).values_list("category_id", flat=True)
    liked_tags = Blog.objects.filter(likes=user).values_list("tags__id", flat=True)
    qs = (
        Blog.objects.published()
        .with_relations()
        .with_counts()
        .exclude(author=user)
        .filter(
            Q(category_id__in=list(liked_categories))
            | Q(tags__id__in=list(liked_tags))
        )
        .distinct()
        .order_by("-view_count")
    )
    return qs[:limit] or popular_posts(limit)


# ---------------------------------------------------------------------------
# View tracking
# ---------------------------------------------------------------------------
def track_view(request, blog):
    """Record a unique view (once per ip+session) and bump the counter."""
    ip = request.META.get("REMOTE_ADDR") or None
    session_key = request.session.session_key or ""
    if not session_key:
        request.session["seen"] = True  # force a session to exist
        request.session.save()
        session_key = request.session.session_key or ""

    fingerprint = hashlib.sha256(f"{ip}|{session_key}".encode()).hexdigest()[:64]
    request.session[f"viewed_{blog.pk}"] = fingerprint

    try:
        blog.views.create(viewer_ip=ip, session_key=fingerprint)
        Blog.objects.filter(pk=blog.pk).update(view_count=F("view_count") + 1)
    except Exception:  # unique constraint => already counted
        pass


def has_viewed(request, blog):
    key = f"viewed_{blog.pk}"
    return key in request.session and request.session[key]
