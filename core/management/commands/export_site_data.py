"""Export site content + users from the current database to a JSON file.

Run on local (SQLite) machine, then commit the JSON so the import command
can load the same data into the production (PostgreSQL) database.

    python manage.py export_site_data --output site_data.json
"""

import json
from datetime import date, datetime, time

from django.core.management.base import BaseCommand, CommandError
from django.db.models.fields.files import FieldFile
from django.utils.dateparse import parse_date, parse_datetime, parse_time


class Command(BaseCommand):
    help = "Export all site data to a JSON file."

    def add_arguments(self, parser):
        parser.add_argument("--output", default="site_data.json")

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

        def to_python(value):
            if isinstance(value, FieldFile):
                return value.name or ""
            if isinstance(value, (datetime, date, time)):
                return value.isoformat()
            return value

        data = {
            "users": [
                {
                    **dict((f.attname, to_python(u.__dict__.get(f.attname, getattr(u, f.attname, getattr(u, f.name, None))))) for f in u._meta.fields),
                    "profile": dict((f.attname, to_python(getattr(u.profile, f.attname))) for f in Profile._meta.fields if f.attname != "user_id"),
                }
                for u in User.objects.select_related("profile").all()
            ],
            "categories": [
                dict((f.attname, to_python(getattr(o, f.attname, getattr(o, f.name)))) for f in o._meta.fields)
                for o in Category.objects.all()
            ],
            "tags": [
                dict((f.attname, to_python(getattr(o, f.attname, getattr(o, f.name)))) for f in o._meta.fields)
                for o in Tag.objects.all()
            ],
            "blogs": [
                {
                    **dict((f.attname, to_python(getattr(o, f.attname, getattr(o, f.name)))) for f in o._meta.fields),
                    "tag_ids": list(o.tags.values_list("id", flat=True)),
                    "like_ids": list(o.likes.values_list("id", flat=True)),
                    "bookmark_ids": list(o.bookmarks.values_list("id", flat=True)),
                }
                for o in Blog.objects.all()
            ],
            "comments": [
                {
                    **dict((f.attname, to_python(getattr(o, f.attname, getattr(o, f.name)))) for f in o._meta.fields),
                    "like_ids": list(o.likes.values_list("id", flat=True)),
                }
                for o in Comment.objects.all()
            ],
            "blog_views": [
                dict((f.attname, to_python(getattr(o, f.attname, getattr(o, f.name)))) for f in o._meta.fields)
                for o in BlogView.objects.all()
            ],
            "newsletter": [
                dict((f.attname, to_python(getattr(o, f.attname, getattr(o, f.name)))) for f in o._meta.fields)
                for o in NewsletterSubscriber.objects.all()
            ],
            "contact": [
                dict((f.attname, to_python(getattr(o, f.attname, getattr(o, f.name)))) for f in o._meta.fields)
                for o in ContactMessage.objects.all()
            ],
            "search_history": [
                dict((f.attname, to_python(getattr(o, f.attname, getattr(o, f.name)))) for f in o._meta.fields)
                for o in SearchHistory.objects.all()
            ],
        }

        out = options["output"]
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2, default=str)
        self.stdout.write(self.style.SUCCESS(f"Exported to {out}"))

        # Guard against accidental empty exports.
        if not data["users"] or not data["blogs"]:
            raise CommandError(
                "Export produced no users/blogs — refusing to write an empty dump. "
                "Point DATABASE_URL at your local SQLite before exporting."
            )