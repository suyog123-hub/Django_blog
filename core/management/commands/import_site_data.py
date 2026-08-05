"""Import site content + users from a JSON dump into the current database.

Run AFTER `migrate` on the target (production) database. Idempotent: existing
records are matched by primary key and updated rather than duplicated, so it is
safe to run on every deploy.

    python manage.py import_site_data --input site_data.json
"""

import json
import os

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import CharField


class Command(BaseCommand):
    help = "Load site data exported by export_site_data."

    def add_arguments(self, parser):
        parser.add_argument("--input", default="site_data.json")

    @transaction.atomic
    def handle(self, *args, **options):
        from core.models import (
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
        from django.contrib.auth.models import User

        src = options["input"]
        if not os.path.exists(src):
            self.stdout.write(self.style.WARNING(f"No dump at {src} — skipping import."))
            return

        from core.models import Blog as _Blog

        if _Blog.objects.exists():
            self.stdout.write(
                self.style.WARNING("Database already has blogs — skipping seed import (keeps production data intact).")
            )
            return

        with open(src, encoding="utf-8") as fh:
            data = json.load(fh)

        # ---- Users + profiles (preserve IDs, passwords, dates) ----------
        for item in data.get("users", []):
            profile = item.pop("profile", {})
            uid = item.pop("id")
            u, _ = User.objects.update_or_create(
                pk=uid,
                defaults={k: v for k, v in item.items() if k != "password"},
            )
            u.password = item["password"]  # keep the original hash so logins still work
            u.save(update_fields=["password"])
            defaults = {
                k: v
                for k, v in profile.items()
                if k not in ("id", "user_id", "created_at", "updated_at")
            }
            Profile.objects.update_or_create(user_id=uid, defaults=defaults)
        self.stdout.write(self.style.SUCCESS(f"Imported {len(data.get('users', []))} users"))

        # ---- Categories / tags ------------------------------------------
        for item in data.get("categories", []):
            pk = item.pop("id")
            Category.objects.update_or_create(pk=pk, defaults=item)
        for item in data.get("tags", []):
            pk = item.pop("id")
            Tag.objects.update_or_create(pk=pk, defaults=item)
        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {len(data.get('categories', []))} categories, {len(data.get('tags', []))} tags"
            )
        )

        # ---- Blogs --------------------------------------------------------
        known_tags = set(Tag.objects.values_list("id", flat=True))
        known_cats = set(Category.objects.values_list("id", flat=True))
        known_users = set(User.objects.values_list("id", flat=True))
        for item in data.get("blogs", []):
            pk = item.pop("id")
            author_id = item.pop("author_id")
            likes = item.pop("like_ids", [])
            bookmarks = item.pop("bookmark_ids", [])
            tags = item.pop("tag_ids", [])
            if item.get("category_id") not in known_cats:
                item["category_id"] = None
            blog, _ = Blog.objects.update_or_create(
                pk=pk, defaults={**item, "author_id": author_id}
            )
            blog.tags.set([t for t in tags if t in known_tags])
            blog.likes.set([u for u in likes if u in known_users])
            blog.bookmarks.set([u for u in bookmarks if u in known_users])
        self.stdout.write(self.style.SUCCESS(f"Imported {len(data.get('blogs', []))} blogs"))

        # ---- Comments -----------------------------------------------------
        for item in data.get("comments", []):
            pk = item.pop("id")
            likes = item.pop("like_ids", [])
            comment, _ = Comment.objects.update_or_create(pk=pk, defaults=item)
            comment.likes.set([u for u in likes if u in known_users])

        # ---- Misc ----------------------------------------------------------
        for item in data.get("blog_views", []):
            pk = item.pop("id")
            BlogView.objects.update_or_create(pk=pk, defaults=item)
        for item in data.get("newsletter", []):
            pk = item.pop("id")
            NewsletterSubscriber.objects.update_or_create(pk=pk, defaults=item)
        for item in data.get("contact", []):
            pk = item.pop("id")
            ContactMessage.objects.update_or_create(pk=pk, defaults=item)
        for item in data.get("search_history", []):
            pk = item.pop("id")
            SearchHistory.objects.update_or_create(pk=pk, defaults=item)

        self.stdout.write(self.style.SUCCESS("Import complete."))