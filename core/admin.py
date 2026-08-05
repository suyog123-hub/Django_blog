"""Django admin configuration with rich list views, previews and actions."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.db.models import Count, Sum
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone

from .models import (
    Blog,
    BlogView,
    Category,
    Comment,
    ContactMessage,
    NewsletterSubscriber,
    Profile,
    SearchHistory,
    Tag,
)


def _thumbnail(obj, field="cover_image", width="64"):
    image = getattr(obj, field, None)
    if not image:
        return format_html("<span style='color:#94a3b8'>—</span>")
    return format_html(
        '<img src="{}" style="width:{}px;height:{}px;object-fit:cover;'
        'border-radius:8px;" loading="lazy"/>',
        image.url,
        width,
        width,
    )


class BlogInline(admin.TabularInline):
    model = Blog
    extra = 0
    fields = ("title", "status", "view_count")
    show_change_link = True
    can_delete = False


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "avatar_preview", "location", "followers_count", "email_verified", "created_at")
    search_fields = ("user__username", "user__email", "bio", "location")
    readonly_fields = ("avatar_preview",)
    autocomplete_fields = ("user",)

    def avatar_preview(self, obj):
        return _thumbnail(obj, "avatar", width="48")

    avatar_preview.short_description = "Avatar"

    @admin.display(description="Followers")
    def followers_count(self, obj):
        return obj.followers.count()


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "blog_count", "description")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("blog_count",)

    @admin.display(description="Posts")
    def blog_count(self, obj):
        return obj.blogs.count()


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "blog_count")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="Posts")
    def blog_count(self, obj):
        return obj.blogs.count()


@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = (
        "thumbnail",
        "title",
        "author",
        "category",
        "status",
        "view_count",
        "like_count",
        "is_featured",
        "is_trending",
        "published_at",
    )
    list_filter = ("status", "is_featured", "is_trending", "is_editor_pick", "category", "author")
    search_fields = ("title", "content", "excerpt", "tags__name", "author__username")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("author", "category", "tags")
    readonly_fields = ("thumbnail", "view_count", "created_at", "updated_at", "like_count", "bookmark_count")
    date_hierarchy = "published_at"
    list_per_page = 25

    fieldsets = (
        (
            "Content",
            {"fields": ("thumbnail", "title", "slug", "excerpt", "content", "cover_image", "cover_alt")},
        ),
        (
            "Publication",
            {
                "fields": (
                    "author",
                    "category",
                    "tags",
                    "status",
                    "published_at",
                    "is_featured",
                    "is_trending",
                    "is_editor_pick",
                )
            },
        ),
        (
            "Engagement",
            {"fields": ("view_count", "like_count", "bookmark_count", "created_at", "updated_at")},
        ),
        ("SEO", {"fields": ("seo_title", "seo_description"), "classes": ("collapse",)}),
    )

    actions = ("publish_selected", "unpublish_selected", "feature_selected", "unfeature_selected")

    @admin.display(description="Cover")
    def thumbnail(self, obj):
        return _thumbnail(obj)

    @admin.display(description="Likes")
    def like_count(self, obj):
        return obj.likes.count()

    @admin.display(description="Bookmarks")
    def bookmark_count(self, obj):
        return obj.bookmarks.count()

    @admin.action(description="Publish selected posts")
    def publish_selected(self, request, queryset):
        updated = queryset.update(
            status=Blog.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        self.message_user(request, f"{updated} post(s) published.")

    @admin.action(description="Move to draft")
    def unpublish_selected(self, request, queryset):
        updated = queryset.update(status=Blog.Status.DRAFT, published_at=None)
        self.message_user(request, f"{updated} post(s) moved to draft.")

    @admin.action(description="Feature selected posts")
    def feature_selected(self, request, queryset):
        queryset.update(is_featured=True)
        self.message_user(request, "Selected posts marked as featured.")

    @admin.action(description="Remove featured flag")
    def unfeature_selected(self, request, queryset):
        queryset.update(is_featured=False)
        self.message_user(request, "Featured flag removed.")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("preview", "blog", "author", "parent", "like_count", "is_approved", "created_at")
    list_filter = ("is_approved", "created_at")
    search_fields = ("content", "author__username", "blog__title")
    actions = ("approve_comments", "disapprove_comments")

    def preview(self, obj):
        return format_html(f'<span style="max-width:260px;display:inline-block">{obj.content[:70]}…</span>')

    preview.short_description = "Comment"

    @admin.display(description="Likes")
    def like_count(self, obj):
        return obj.likes.count()

    @admin.action(description="Approve selected comments")
    def approve_comments(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, "Comments approved.")

    @admin.action(description="Unapprove selected comments")
    def disapprove_comments(self, request, queryset):
        queryset.update(is_approved=False)
        self.message_user(request, "Comments unapproved.")


@admin.register(BlogView)
class BlogViewAdmin(admin.ModelAdmin):
    list_display = ("blog", "viewer_ip", "session_key", "created_at")
    search_fields = ("blog__title", "viewer_ip")
    list_filter = ("created_at",)
    readonly_fields = ("blog", "viewer_ip", "session_key", "created_at")
    list_per_page = 50


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("email",)
    actions = ("activate", "deactivate")

    @admin.action(description="Mark as active")
    def activate(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="Unsubscribe selected")
    def deactivate(self, request, queryset):
        queryset.update(is_active=False)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "is_read", "created_at")
    list_filter = ("is_read",)
    search_fields = ("name", "email", "subject", "message")
    readonly_fields = ("name", "email", "subject", "message", "created_at")
    actions = ("mark_read",)

    @admin.action(description="Mark as read")
    def mark_read(self, request, queryset):
        queryset.update(is_read=True)


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ("query", "user", "created_at")
    search_fields = ("query", "user__username")
    list_filter = ("created_at",)


# Re-register the auth User to expose the profile inline.
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    fields = ("avatar", "bio", "location", "website", "twitter", "github", "linkedin", "email_verified")


class CustomUserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_superuser", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
