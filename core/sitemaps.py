"""Sitemap generation for SEO."""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone

from .models import Blog, Category, Tag


class StaticViewSitemap(Sitemap):
    """Home page and other static routes."""

    changefreq = "weekly"
    priority = 0.5

    def items(self):
        return ["home", "blogs", "authors", "contact"]

    def location(self, item):
        return reverse(item)


class BlogSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.9

    def items(self):
        return Blog.objects.published()

    def lastmod(self, obj):
        return obj.updated_at


class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Category.objects.filter(blogs__status=Blog.Status.PUBLISHED).distinct()

    def lastmod(self, obj):
        return obj.updated_at


class TagSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.4

    def items(self):
        return Tag.objects.filter(blogs__status=Blog.Status.PUBLISHED).distinct()
