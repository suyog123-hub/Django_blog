from django.conf import settings


def separate_admin_session(get_response):
    def middleware(request):
        if request.path.startswith("/admin/"):
            settings.SESSION_COOKIE_NAME = "admin_sessionid"
        else:
            settings.SESSION_COOKIE_NAME = "sessionid"
        response = get_response(request)
        return response

    return middleware
