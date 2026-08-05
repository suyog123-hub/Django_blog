"""Site-wide context injected into every template."""

from django.db.models import Count

from .models import Blog, Category, Tag


def site_context(request):
    """Provide global navigation data (categories, tags, hot posts, theme)."""
    categories = (
        Category.objects.annotate(blog_count=Count("blogs"))
        .filter(blog_count__gt=0)
        .order_by("-blog_count")[:8]
    )
    tags = Tag.objects.annotate(blog_count=Count("blogs")).filter(
        blog_count__gt=0
    ).order_by("-blog_count")[:15]

    return {
        "nav_categories": categories,
        "nav_tags": tags,
        "current_path": request.path,
        "site_name": "Inkwell",
        "is_search_page": request.path == "/search/",
    }
