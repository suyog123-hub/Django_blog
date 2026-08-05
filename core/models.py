"""
Core data models for the blogging platform.

Design notes
------------
* The built-in ``auth.User`` model is used (rather than a custom user model)
  so existing accounts are preserved. User-specific data lives on
  :class:`Profile`, wired via a post-save signal.
* :class:`Blog` uses a ``slug`` for SEO friendly URLs, a ``status`` field
  for the draft / published / archived workflow and a nullable
  ``published_at`` to support scheduled publishing.
* Custom managers / querysets centralise query logic so views stay lean
  and database access is optimised (``select_related`` / ``prefetch_related``).
"""

from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, URLValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    """Abstract base model that records creation/update timestamps."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ---------------------------------------------------------------------------
# Taxonomy
# ---------------------------------------------------------------------------
class Category(TimeStampedModel):
    """Blog categories, e.g. Technology, Lifestyle, Travel."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, default="fa-folder")

    class Meta:
        verbose_name_plural = "categories"
        ordering = ("name",)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blogs_by_category", kwargs={"slug": self.slug})

    @property
    def published_blogs(self):
        return Blog.objects.published().filter(category=self)


class Tag(TimeStampedModel):
    """Lightweight tags attached to blog posts."""

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blogs_by_tag", kwargs={"tag_slug": self.slug})


# ---------------------------------------------------------------------------
# User profile
# ---------------------------------------------------------------------------
class Profile(TimeStampedModel):
    """Extra information about a user (avatar, bio, social links, followers)."""

    GENDER_CHOICES = (
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=120, blank=True)
    website = models.URLField(max_length=255, blank=True)
    twitter = models.CharField(max_length=120, blank=True)
    github = models.CharField(max_length=120, blank=True)
    linkedin = models.CharField(max_length=120, blank=True)
    email_verified = models.BooleanField(default=False)
    followers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="following_profiles",
        blank=True,
    )

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user.username}'s profile"

    @property
    def followers_count(self):
        return self.followers.count()

    @property
    def following_count(self):
        return User.objects.filter(profile__followers=self.user).count()

    @property
    def total_views(self):
        return Blog.objects.filter(author=self.user).aggregate(
            total=models.Sum("view_count")
        )["total"] or 0

    @property
    def total_likes(self):
        return Blog.objects.filter(author=self.user).aggregate(
            total=models.Count("likes")
        )["total"] or 0


# ---------------------------------------------------------------------------
# Blog
# ---------------------------------------------------------------------------
class BlogQuerySet(models.QuerySet):
    """Reusable, chainable querysets for blog posts."""

    def published(self):
        now = timezone.now()
        return self.filter(
            status=Blog.Status.PUBLISHED,
            published_at__lte=now,
        )

    def drafts(self):
        return self.filter(status=Blog.Status.DRAFT)

    def scheduled(self):
        now = timezone.now()
        return self.filter(
            status=Blog.Status.PUBLISHED,
            published_at__gt=now,
        )

    def featured(self):
        return self.filter(is_featured=True)

    def trending(self):
        return self.filter(is_trending=True)

    def editor_picks(self):
        return self.filter(is_editor_pick=True)

    def by_author(self, user):
        return self.filter(author=user)

    def with_relations(self):
        """Avoid N+1 queries when rendering cards / detail pages."""
        return self.select_related("author", "author__profile", "category").prefetch_related(
            "tags"
        )

    def with_counts(self):
        return self.annotate(
            like_count=models.Count("likes", distinct=True),
            comment_count=models.Count("comments", distinct=True),
        )

    def search(self, query):
        """Case-insensitive search across title, content, tags and author."""
        return self.published().filter(
            models.Q(title__icontains=query)
            | models.Q(excerpt__icontains=query)
            | models.Q(content__icontains=query)
            | models.Q(tags__name__icontains=query)
            | models.Q(author__username__icontains=query)
        ).distinct()


class BlogManager(models.Manager):
    def get_queryset(self):
        return BlogQuerySet(self.model, using=self._db)

    def published(self):
        return self.get_queryset().published()

    def drafts(self):
        return self.get_queryset().drafts()

    def scheduled(self):
        return self.get_queryset().scheduled()

    def featured(self):
        return self.get_queryset().featured()

    def trending(self):
        return self.get_queryset().trending()

    def editor_picks(self):
        return self.get_queryset().editor_picks()

    def by_author(self, user):
        return self.get_queryset().by_author(user)

    def with_relations(self):
        return self.get_queryset().with_relations()

    def with_counts(self):
        return self.get_queryset().with_counts()

    def search(self, query):
        return self.get_queryset().search(query)


def unique_slugify(instance, value, queryset=None):
    """Generate a unique slug for *instance* based on *value*."""
    base = slugify(value)[:120] or "untitled"
    queryset = queryset or instance.__class__._default_manager
    slug = base
    counter = 1
    while queryset.filter(slug=slug).exclude(pk=instance.pk).exists():
        counter += 1
        slug = f"{base}-{counter}"
    return slug


class Blog(TimeStampedModel):
    """A single blog post / article."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    title = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, db_index=True, blank=True)
    content = models.TextField()
    excerpt = models.TextField(max_length=500, blank=True, help_text="Short summary shown on cards.")
    cover_image = models.ImageField(
        upload_to="blogs/", blank=True, null=True,
        help_text="Featured / hero cover image.",
    )
    cover_alt = models.CharField(max_length=255, blank=True)

    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="blogs"
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, related_name="blogs", null=True, blank=True
    )
    tags = models.ManyToManyField(Tag, related_name="blogs", blank=True)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    published_at = models.DateTimeField(
        null=True, blank=True, db_index=True,
        help_text="When the post goes (or went) live. Leave blank to publish now.",
    )

    is_featured = models.BooleanField(default=False, db_index=True)
    is_trending = models.BooleanField(default=False, db_index=True)
    is_editor_pick = models.BooleanField(default=False, db_index=True)

    view_count = models.PositiveIntegerField(default=0, db_index=True)

    seo_title = models.CharField(max_length=70, blank=True)
    seo_description = models.CharField(max_length=160, blank=True)

    likes = models.ManyToManyField(
        User, related_name="liked_blogs", blank=True
    )
    bookmarks = models.ManyToManyField(
        User, related_name="bookmarked_blogs", blank=True
    )

    objects = BlogManager()

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status", "published_at", "-view_count"]),
            models.Index(fields=["author", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(view_count__gte=0), name="view_count_non_negative"
            )
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.title)
        if not self.excerpt and self.content:
            self.excerpt = self.content[:300]
        if not self.published_at and self.status == self.Status.PUBLISHED:
            self.published_at = timezone.now()
        if self.status != self.Status.PUBLISHED:
            self.published_at = None
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blog_detail", kwargs={"slug": self.slug})

    # -- Derived helpers ---------------------------------------------------
    @property
    def is_published(self):
        return self.status == self.Status.PUBLISHED and (
            not self.published_at or self.published_at <= timezone.now()
        )

    @property
    def reading_time_minutes(self):
        """Estimate reading time based on a ~200 wpm reading speed."""
        words = len(self.content.split())
        return max(1, round(words / 200))

    @property
    def bookmark_count(self):
        return self.bookmarks.count()

    def is_liked_by(self, user):
        if not user.is_authenticated:
            return False
        return self.likes.filter(pk=user.pk).exists()

    def is_bookmarked_by(self, user):
        if not user.is_authenticated:
            return False
        return self.bookmarks.filter(pk=user.pk).exists()


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------
class Comment(TimeStampedModel):
    """Nested comments; a parent comment enables threaded replies."""

    blog = models.ForeignKey(
        Blog, on_delete=models.CASCADE, related_name="comments"
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="comments"
    )
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, related_name="replies", null=True, blank=True
    )
    content = models.TextField(max_length=2000)
    is_approved = models.BooleanField(default=True, db_index=True)
    likes = models.ManyToManyField(User, related_name="liked_comments", blank=True)

    class Meta:
        ordering = ("created_at",)

    def __str__(self):
        return f"{self.author} on {self.blog}"

    @property
    def like_count(self):
        return self.likes.count()


# ---------------------------------------------------------------------------
# Engagement / tracking
# ---------------------------------------------------------------------------
class BlogView(TimeStampedModel):
    """One row per unique view, keyed by viewer ip + session."""

    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name="views")
    viewer_ip = models.GenericIPAddressField(null=True, blank=True)
    session_key = models.CharField(max_length=40, blank=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["blog", "viewer_ip", "session_key"], name="unique_view_per_visitor"
            )
        ]

    def __str__(self):
        return f"{self.blog} viewed"


class NewsletterSubscriber(TimeStampedModel):
    """People who subscribed to the newsletter."""

    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    token = models.CharField(max_length=64, blank=True, editable=False)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.email


class ContactMessage(TimeStampedModel):
    """Messages submitted through the contact form."""

    name = models.CharField(max_length=150)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField(max_length=3000)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.name}: {self.subject}"


class SearchHistory(TimeStampedModel):
    """Saved searches so users can revisit their queries."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="search_history", null=True, blank=True
    )
    query = models.CharField(max_length=200)
    session_key = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.query


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------
from django.db.models.signals import post_save  # noqa: E402
from django.dispatch import receiver  # noqa: E402


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Ensure every user has a profile (and keep it up to date)."""
    if created:
        Profile.objects.create(user=instance)
    else:
        Profile.objects.get_or_create(user=instance)
