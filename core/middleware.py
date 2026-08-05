"""
Middleware for the blog project.

``separate_admin_session`` keeps the Django admin on its own session cookie so
an admin logged into the backend is not automatically logged into the public
site (and vice versa).
"""

from django.conf import settings

ADMIN_SESSION_COOKIE = "admin_sessionid"
PUBLIC_SESSION_COOKIE = "sessionid"


def separate_admin_session(get_response):
    def middleware(request):
        original = settings.SESSION_COOKIE_NAME
        try:
            if request.path.startswith("/admin/"):
                settings.SESSION_COOKIE_NAME = ADMIN_SESSION_COOKIE
            else:
                settings.SESSION_COOKIE_NAME = PUBLIC_SESSION_COOKIE
            response = get_response(request)
        finally:
            settings.SESSION_COOKIE_NAME = original
        return response

    return middleware
