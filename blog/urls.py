"""
Root URL configuration.

Includes the core app, Django admin, media serving and SEO endpoints
(``sitemap.xml`` and ``robots.txt``).
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps import views as sitemap_views
from django.http import HttpResponse
from django.urls import include, path, re_path
from django.views.static import serve

from core.sitemaps import BlogSitemap, CategorySitemap, StaticViewSitemap, TagSitemap

sitemaps = {
    "static": StaticViewSitemap,
    "blogs": BlogSitemap,
    "categories": CategorySitemap,
    "tags": TagSitemap,
}


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /accounts/",
        "Disallow: /search/",
        "",
        "Sitemap: {}/sitemap.xml".format(request.build_absolute_uri("/").rstrip("/")),
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("sitemap.xml", sitemap_views.index, {"sitemaps": sitemaps}, name="sitemap"),
    path(
        "sitemap-<section>.xml",
        sitemap_views.sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path("robots.txt", robots_txt, name="robots"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += [
        re_path(
            r"^" + settings.MEDIA_URL.lstrip("/") + r"(?P<path>.*)$",
            serve,
            {"document_root": settings.MEDIA_ROOT},
        ),
    ]
