# Generated manually to preserve existing blog data during the redesign.

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


def backfill_blog_data(apps, schema_editor):
    """Backfill new fields from legacy columns and prepare users' profiles."""
    Blog = apps.get_model("core", "Blog")
    Profile = apps.get_model("core", "Profile")
    User = apps.get_model("auth", "User")
    from django.utils.text import slugify

    for blog in Blog.objects.all():
        if not blog.slug:
            base = slugify(blog.title)[:120] or "untitled"
            slug = base
            counter = 1
            while Blog.objects.filter(slug=slug).exclude(pk=blog.pk).exists():
                counter += 1
                slug = f"{base}-{counter}"
            blog.slug = slug
        if not blog.excerpt and blog.content:
            blog.excerpt = blog.content[:300]
        # Legacy posts that were approved become published immediately.
        if blog.is_approved:
            blog.status = "published"
            blog.published_at = blog.created_at
        blog.save()

    for user in User.objects.all():
        Profile.objects.get_or_create(user=user)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="blog",
            options={"ordering": ("-created_at",)},
        ),
        # --- Legacy field renames (preserves data) -------------------------
        migrations.RenameField(
            model_name="blog",
            old_name="created_date",
            new_name="created_at",
        ),
        migrations.RenameField(
            model_name="blog",
            old_name="image",
            new_name="cover_image",
        ),
        # --- New taxonomy models -------------------------------------------
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=100, unique=True)),
                ("slug", models.SlugField(max_length=120, unique=True, blank=True)),
                ("description", models.TextField(blank=True)),
                ("icon", models.CharField(max_length=50, blank=True, default="fa-folder")),
            ],
            options={"verbose_name_plural": "categories", "ordering": ("name",)},
        ),
        migrations.CreateModel(
            name="Tag",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=50, unique=True)),
                ("slug", models.SlugField(max_length=60, unique=True, blank=True)),
            ],
            options={"ordering": ("name",)},
        ),
        migrations.CreateModel(
            name="Profile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("avatar", models.ImageField(blank=True, null=True, upload_to="avatars/")),
                ("bio", models.TextField(blank=True, max_length=500)),
                ("location", models.CharField(blank=True, max_length=120)),
                ("website", models.URLField(blank=True, max_length=255)),
                ("twitter", models.CharField(blank=True, max_length=120)),
                ("github", models.CharField(blank=True, max_length=120)),
                ("linkedin", models.CharField(blank=True, max_length=120)),
                ("email_verified", models.BooleanField(default=False)),
                (
                    "user",
                    models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="BlogView",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("viewer_ip", models.GenericIPAddressField(blank=True, null=True)),
                ("session_key", models.CharField(blank=True, db_index=True, max_length=40)),
                ("blog", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="views", to="core.blog")),
            ],
        ),
        migrations.CreateModel(
            name="Comment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("content", models.TextField(max_length=2000)),
                ("is_approved", models.BooleanField(default=True, db_index=True)),
                ("author", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="comments", to=settings.AUTH_USER_MODEL)),
                ("blog", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="comments", to="core.blog")),
                ("likes", models.ManyToManyField(blank=True, related_name="liked_comments", to=settings.AUTH_USER_MODEL)),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="replies", to="core.comment")),
            ],
            options={"ordering": ("created_at",)},
        ),
        migrations.CreateModel(
            name="ContactMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=150)),
                ("email", models.EmailField(max_length=254)),
                ("subject", models.CharField(max_length=200)),
                ("message", models.TextField(max_length=3000)),
                ("is_read", models.BooleanField(default=False)),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="NewsletterSubscriber",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("is_active", models.BooleanField(default=True)),
                ("token", models.CharField(blank=True, editable=False, max_length=64)),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="SearchHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("query", models.CharField(max_length=200)),
                ("session_key", models.CharField(blank=True, max_length=40)),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="search_history", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at",)},
        ),
        # --- New Blog fields ------------------------------------------------
        migrations.AddField(
            model_name="blog",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name="blog",
            name="excerpt",
            field=models.TextField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="blog",
            name="slug",
            field=models.SlugField(blank=True, max_length=255, unique=False),
        ),
        migrations.AddField(
            model_name="blog",
            name="cover_alt",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="blog",
            name="category",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="blogs", to="core.category"),
        ),
        migrations.AddField(
            model_name="blog",
            name="tags",
            field=models.ManyToManyField(blank=True, related_name="blogs", to="core.tag"),
        ),
        migrations.AddField(
            model_name="blog",
            name="status",
            field=models.CharField(choices=[("draft", "Draft"), ("published", "Published"), ("archived", "Archived")], db_index=True, default="draft", max_length=20),
        ),
        migrations.AddField(
            model_name="blog",
            name="published_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="blog",
            name="is_featured",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="blog",
            name="is_trending",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="blog",
            name="is_editor_pick",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="blog",
            name="view_count",
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
        migrations.AddField(
            model_name="blog",
            name="seo_title",
            field=models.CharField(blank=True, max_length=70),
        ),
        migrations.AddField(
            model_name="blog",
            name="seo_description",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="blog",
            name="likes",
            field=models.ManyToManyField(blank=True, related_name="liked_blogs", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="blog",
            name="bookmarks",
            field=models.ManyToManyField(blank=True, related_name="bookmarked_blogs", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name="blog",
            name="title",
            field=models.CharField(db_index=True, max_length=255),
        ),
        # --- Constraints & indexes ------------------------------------------
        migrations.AddIndex(
            model_name="blog",
            index=models.Index(fields=["status", "published_at", "-view_count"], name="core_blog_status_pub_3b0f21_idx"),
        ),
        migrations.AddIndex(
            model_name="blog",
            index=models.Index(fields=["author", "status"], name="core_blog_author__d5f614_idx"),
        ),
        migrations.AddConstraint(
            model_name="blog",
            constraint=models.CheckConstraint(condition=models.Q(("view_count__gte", 0)), name="view_count_non_negative"),
        ),
        migrations.AddField(
            model_name="profile",
            name="followers",
            field=models.ManyToManyField(blank=True, related_name="following_profiles", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddConstraint(
            model_name="blogview",
            constraint=models.UniqueConstraint(fields=("blog", "viewer_ip", "session_key"), name="unique_view_per_visitor"),
        ),
        # --- Data migration --------------------------------------------------
        migrations.RunPython(backfill_blog_data, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="blog",
            name="slug",
            field=models.SlugField(blank=True, max_length=255, unique=True),
        ),
        migrations.RemoveField(
            model_name="blog",
            name="is_approved",
        ),
    ]
