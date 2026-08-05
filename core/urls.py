"""URL routing for the core application."""

from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    # --- Home & browsing ---------------------------------------------------
    path("", views.home_page, name="home"),
    path("blogs/", views.blog_list_page, name="blogs"),
    path(
        "blogs/category/<slug:category_slug>/",
        views.blog_list_page,
        name="blogs_by_category",
    ),
    path(
        "blogs/tag/<slug:tag_slug>/",
        views.blog_list_page,
        name="blogs_by_tag",
    ),
    path("blog/<slug:slug>/", views.blog_detail_page, name="blog_detail"),
    path("authors/", views.authors_page, name="authors"),

    # --- Search ------------------------------------------------------------
    path("search/", views.search_page, name="search"),
    path("search/suggest/", views.search_suggestions, name="search_suggestions"),

    # --- Authentication ----------------------------------------------------
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    path(
        "accounts/password_reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            email_template_name="registration/password_reset_email.html",
            subject_template_name="registration/password_reset_subject.txt",
        ),
        name="password_reset",
    ),
    path(
        "accounts/password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "accounts/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "accounts/reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    path(
        "accounts/password_change/",
        auth_views.PasswordChangeView.as_view(
            template_name="registration/password_change_form.html"
        ),
        name="password_change",
    ),
    path(
        "accounts/password_change/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="registration/password_change_done.html"
        ),
        name="password_change_done",
    ),

    path("verify-email/", views.send_verification_email, name="send_verification"),
    path(
        "verify-email/<uidb64>/<token>/",
        views.verify_email,
        name="verify_email",
    ),

    # --- Profile -----------------------------------------------------------
    path("@<str:username>/", views.profile_detail, name="profile_detail"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
    path("profile/bookmarks/", views.saved_articles, name="saved_articles"),
    path("follow/<str:username>/", views.toggle_follow, name="toggle_follow"),

    # --- Authoring ---------------------------------------------------------
    path("write/", views.blog_create, name="blog_create"),
    path("write/<slug:slug>/", views.blog_edit, name="blog_edit"),
    path("write/<slug:slug>/autosave/", views.autosave_draft, name="autosave"),
    path("upload/image/", views.upload_image, name="upload_image"),
    path("my-blogs/", views.my_blogs, name="my_blogs"),
    path("delete/<int:pk>/", views.delete_blog, name="delete_blog"),

    # --- Engagement (AJAX) -------------------------------------------------
    path("like/<int:pk>/", views.toggle_like, name="toggle_like"),
    path("bookmark/<int:pk>/", views.toggle_bookmark, name="toggle_bookmark"),
    path("comment/<int:pk>/", views.add_comment, name="add_comment"),
    path("comment-like/<int:pk>/", views.toggle_comment_like, name="toggle_comment_like"),

    # --- Moderation --------------------------------------------------------
    path("pending/", views.pending_blogs, name="pending"),
    path("approve/<int:pk>/", views.approve_blog, name="approve_blog"),
    path("feature/<int:pk>/", views.feature_blog, name="feature_blog"),

    # --- Contact & newsletter ----------------------------------------------
    path("contact/", views.contact_page, name="contact"),
    path(
        "newsletter/subscribe/",
        views.newsletter_subscribe,
        name="newsletter_subscribe",
    ),
    path(
        "newsletter/unsubscribe/<str:token>/",
        views.newsletter_unsubscribe,
        name="newsletter_unsubscribe",
    ),
]

handler404 = "core.views.handler404_view"
