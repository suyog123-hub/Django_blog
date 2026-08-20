"""
Application views.

Views are intentionally thin: business logic lives in ``services.py`` and
forms in ``forms.py``. Authentication pages that do not need custom logic
are wired directly to Django's built-in views in ``urls.py``.
"""

import json
import secrets

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from . import services
from .forms import (
    BlogForm,
    ChangePasswordForm,
    CommentForm,
    ContactForm,
    LoginForm,
    NewsletterForm,
    ProfileForm,
    RegistrationForm,
    UserProfileForm,
)
from .models import (
    Blog,
    Category,
    Comment,
    NewsletterSubscriber,
    SearchHistory,
    Tag,
)
from .services import track_view

PAGE_SIZE = 9
SEARCH_SUGGESTION_LIMIT = 6


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _paginate(queryset, request, per_page=PAGE_SIZE):
    paginator = Paginator(queryset, per_page)
    page = paginator.get_page(request.GET.get("page"))
    query_params = request.GET.copy()
    query_params.pop("page", None)
    query_string = query_params.urlencode()
    return paginator, page, query_string


def _save_search_history(request, query):
    query = query.strip()[:200]
    if not query:
        return
    SearchHistory.objects.create(
        user=request.user if request.user.is_authenticated else None,
        query=query,
        session_key=request.session.session_key or "",
    )
    # Keep history tidy: max 20 per user / session.
    qs = SearchHistory.objects.filter(
        user=request.user if request.user.is_authenticated else None,
        session_key=request.session.session_key or "",
    )
    for record in qs.order_by("-created_at")[20:]:
        record.delete()


# ---------------------------------------------------------------------------
# Home
# ---------------------------------------------------------------------------
def home_page(request):
    """Landing page with hero, featured, trending, picks, latest and more."""
    latest = services.Blog.objects.published().with_relations().with_counts()[:6]
    featured = services.Blog.objects.published().featured().with_relations().with_counts()[:3]
    trending = services.trending_posts(limit=4)
    editor_picks = services.Blog.objects.published().editor_picks().with_relations().with_counts()[:3]
    popular = services.popular_posts(limit=5)
    recommended = services.recommended_for(request.user, limit=3)

    categories = (
        Category.objects.annotate(blog_count=Count("blogs"))
        .filter(blog_count__gt=0)
        .order_by("-blog_count")[:6]
    )
    top_authors = (
        User.objects.annotate(
            published_count=Count(
                "blogs",
                filter=Q(
                    blogs__status=Blog.Status.PUBLISHED,
                    blogs__published_at__lte=timezone.now(),
                ),
            ),
            total_views=Count("blogs__likes"),
        )
        .filter(published_count__gt=0)
        .order_by("-published_count")[:4]
    )

    stats = {
        "articles": services.Blog.objects.published().count(),
        "authors": User.objects.filter(blogs__status=Blog.Status.PUBLISHED).distinct().count(),
        "views": services.Blog.objects.aggregate(views=Sum("view_count"))["views"] or 0,
        "likes": services.Blog.objects.aggregate(likes=Count("likes"))["likes"] or 0,
    }

    context = {
        "featured": featured,
        "trending": trending,
        "editor_picks": editor_picks,
        "latest": latest,
        "popular": popular,
        "recommended": recommended,
        "categories": categories,
        "top_authors": top_authors,
        "stats": stats,
    }
    return render(request, "core/home.html", context)


# ---------------------------------------------------------------------------
# Blog listing
# ---------------------------------------------------------------------------
def random_blog(request):
    """Jump to a random published post. Pure fun, no tracking."""
    blog = services.Blog.objects.published().order_by("?").first()
    if not blog:
        messages.info(request, "No articles yet — check back soon!")
        return redirect("blogs")
    return redirect(blog.get_absolute_url())


def _apply_filters(request, category_slug=None, tag_slug=None):
    qs = Blog.objects.published().with_relations().with_counts()
    filters = {}

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        qs = qs.filter(category=category)
        filters["category"] = category
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        qs = qs.filter(tags=tag)
        filters["tag"] = tag

    query = request.GET.get("q", "").strip()
    if query:
        qs = qs.search(query)
        filters["q"] = query

    author_name = request.GET.get("author", "").strip()
    if author_name:
        qs = qs.filter(author__username__icontains=author_name)
        filters["author"] = author_name

    sort = request.GET.get("sort", "newest")
    if sort == "oldest":
        qs = qs.order_by("created_at")
    elif sort == "popular":
        qs = qs.order_by("-view_count")
    elif sort == "liked":
        qs = qs.order_by("-like_count", "-created_at")
    else:
        qs = qs.order_by("-created_at")
    filters["sort"] = sort

    return qs, filters


def blog_list_page(request, category_slug=None, tag_slug=None):
    qs, filters = _apply_filters(request, category_slug, tag_slug)
    paginator, page, query_string = _paginate(qs, request)

    context = {
        "blogs": page.object_list,
        "paginator": paginator,
        "page_obj": page,
        "query_string": query_string,
        "filters": filters,
        "categories": Category.objects.annotate(c=Count("blogs")).filter(c__gt=0).order_by("-c")[:12],
        "tags": Tag.objects.annotate(c=Count("blogs")).filter(c__gt=0).order_by("-c")[:20],
        "total": paginator.count,
    }
    return render(request, "core/blog_list.html", context)


# ---------------------------------------------------------------------------
# Blog detail
# ---------------------------------------------------------------------------
def blog_detail_page(request, slug):
    blog = get_object_or_404(
        Blog.objects.with_relations()
        .with_counts()
        .prefetch_related("comments__author", "comments__replies", "comments__likes"),
        slug=slug,
    )

    # Non-published posts are private unless you're the author or a staff member.
    if not blog.is_published and not (request.user == blog.author or request.user.is_staff):
        raise Http404("This article is not available yet.")

    if blog.is_published and not request.user.is_staff:
        track_view(request, blog)

    comments = blog.comments.filter(parent__isnull=True, is_approved=True)
    comment_count = sum(1 + c.replies.filter(is_approved=True).count() for c in comments)

    related = services.related_posts(blog, limit=3)
    siblings = list(
        Blog.objects.published().filter(category=blog.category)
        if blog.category
        else Blog.objects.published()
    )
    previous = next_post = None
    for i, item in enumerate(siblings):
        if item.pk == blog.pk:
            previous = siblings[i - 1] if i > 0 else None
            next_post = siblings[i + 1] if i + 1 < len(siblings) else None
            break

    context = {
        "blog": blog,
        "comments": comments,
        "comment_count": comment_count,
        "comment_form": CommentForm(),
        "related": related,
        "previous_post": previous,
        "next_post": next_post,
        "is_liked": blog.is_liked_by(request.user),
        "is_bookmarked": blog.is_bookmarked_by(request.user),
        "is_following_author": (
            request.user.is_authenticated
            and request.user != blog.author
            and blog.author.profile.followers.filter(pk=request.user.pk).exists()
        ),
    }
    return render(request, "core/blog_detail.html", context)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------
def search_page(request):
    query = request.GET.get("q", "").strip()
    results = Blog.objects.none()
    total = 0
    history = SearchHistory.objects.filter(
        user=request.user if request.user.is_authenticated else None,
        session_key=request.session.session_key or "",
    ).values_list("query", flat=True).order_by("-created_at")[:10]

    if query:
        results = Blog.objects.published().with_relations().with_counts().search(query)
        total = results.count()
        _save_search_history(request, query)
    else:
        results = Blog.objects.none().order_by("-created_at")

    sort = request.GET.get("sort", "relevance")
    if sort == "popular":
        results = results.order_by("-view_count")
    elif sort == "liked":
        results = results.order_by("-like_count")
    else:
        results = results.order_by("-created_at")

    paginator, page, query_string = _paginate(results, request)
    context = {
        "query": query,
        "results": page.object_list,
        "page_obj": page,
        "paginator": paginator,
        "query_string": query_string,
        "total": total,
        "history": list(dict.fromkeys(history)),
        "sort": sort,
        "suggested_tags": Tag.objects.annotate(c=Count("blogs")).filter(c__gt=0).order_by("-c")[:8],
    }
    return render(request, "core/search.html", context)


def search_suggestions(request):
    """JSON endpoint used for the live search dropdown."""
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"results": []})

    posts = (
        Blog.objects.published()
        .filter(title__icontains=query)
        .order_by("-view_count")[:SEARCH_SUGGESTION_LIMIT]
    )
    tags = Tag.objects.filter(name__icontains=query)[:4]
    authors = User.objects.filter(username__icontains=query)[:4]
    categories = Category.objects.filter(name__icontains=query)[:4]

    results = []
    for post in posts:
        results.append(
            {
                "type": "post",
                "title": post.title,
                "subtitle": f"{post.author.username} · {post.reading_time_minutes} min read",
                "url": post.get_absolute_url(),
                "image": post.cover_image.url if post.cover_image else "",
            }
        )
    for tag in tags:
        results.append({"type": "tag", "title": f"#{tag.name}", "url": tag.get_absolute_url()})
    for author in authors:
        results.append(
            {
                "type": "author",
                "title": author.username,
                "url": reverse("profile_detail", kwargs={"username": author.username}),
            }
        )
    for category in categories:
        results.append({"type": "category", "title": category.name, "url": category.get_absolute_url()})

    return JsonResponse({"results": results[:12]})


# ---------------------------------------------------------------------------
# Engagement (AJAX)
# ---------------------------------------------------------------------------
@login_required
def toggle_like(request, pk):
    blog = get_object_or_404(Blog, pk=pk)
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    if request.user in blog.likes.all():
        blog.likes.remove(request.user)
        liked = False
    else:
        blog.likes.add(request.user)
        liked = True
    return JsonResponse({"liked": liked, "count": blog.likes.count()})


@login_required
def toggle_bookmark(request, pk):
    blog = get_object_or_404(Blog, pk=pk)
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    if request.user in blog.bookmarks.all():
        blog.bookmarks.remove(request.user)
        saved = False
    else:
        blog.bookmarks.add(request.user)
        saved = True
    return JsonResponse({"saved": saved, "count": blog.bookmarks.count()})


@login_required
def toggle_comment_like(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    if request.user in comment.likes.all():
        comment.likes.remove(request.user)
        liked = False
    else:
        comment.likes.add(request.user)
        liked = True
    return JsonResponse({"liked": liked, "count": comment.likes.count()})


@login_required
def add_comment(request, pk):
    blog = get_object_or_404(Blog, pk=pk)
    if request.method != "POST":
        return redirect(blog.get_absolute_url())
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.blog = blog
        comment.author = request.user
        comment.is_approved = bool(request.user.is_staff)
        if request.POST.get("parent_id"):
            parent = get_object_or_404(Comment, pk=request.POST["parent_id"], blog=blog)
            comment.parent = parent
        comment.save()
        if comment.is_approved:
            messages.success(request, "Comment published.")
        else:
            messages.info(request, "Your comment is awaiting moderation.")
    else:
        messages.error(request, "Comment could not be saved.")
    return redirect(f"{blog.get_absolute_url()}#comments")


@login_required
def edit_comment(request, pk):
    comment = get_object_or_404(
        Comment.objects.select_related("blog", "author"), pk=pk
    )
    if comment.author != request.user and not request.user.is_staff:
        raise PermissionDenied
    if request.method != "POST":
        return redirect(f"{comment.blog.get_absolute_url()}#c-{comment.pk}")
    form = CommentForm(request.POST, instance=comment)
    if form.is_valid():
        form.save()
        messages.success(request, "Comment updated.")
    else:
        messages.error(request, "Comment could not be saved.")
    return redirect(f"{comment.blog.get_absolute_url()}#c-{comment.pk}")


@login_required
def delete_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if comment.author != request.user and not request.user.is_staff:
        raise PermissionDenied
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    url = f"{comment.blog.get_absolute_url()}#comments"
    comment.delete()
    messages.success(request, "Comment deleted.")
    return redirect(url)


@login_required
def toggle_follow(request, username):
    target = get_object_or_404(User, username=username)
    if target == request.user:
        return JsonResponse({"error": "You can't follow yourself."}, status=400)
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    profile = target.profile
    if request.user in profile.followers.all():
        profile.followers.remove(request.user)
        following = False
    else:
        profile.followers.add(request.user)
        following = True
    return JsonResponse({"following": following, "count": profile.followers_count})


# ---------------------------------------------------------------------------
# Contact & newsletter
# ---------------------------------------------------------------------------
def contact_page(request):
    form = ContactForm()
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Thanks for reaching out! We'll get back to you soon.")
            return redirect("contact")
    return render(request, "core/contact.html", {"form": form})


def newsletter_subscribe(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    form = NewsletterForm(request.POST)
    if form.is_valid():
        email = form.cleaned_data["email"]
        subscriber, created = NewsletterSubscriber.objects.get_or_create(
            email=email,
            defaults={"token": secrets.token_hex(16)},
        )
        if not created and not subscriber.is_active:
            subscriber.is_active = True
            subscriber.save()
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": True, "message": "Subscribed! Check your inbox."})
        messages.success(request, "Subscribed! Welcome to the newsletter.")
        return redirect(request.META.get("HTTP_REFERER", "/"))
    error = form.errors.get("email", ["Invalid email."])[0]
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"success": False, "error": error}, status=400)
    messages.error(request, error)
    return redirect(request.META.get("HTTP_REFERER", "/"))


def newsletter_unsubscribe(request, token):
    subscriber = get_object_or_404(NewsletterSubscriber, token=token)
    subscriber.is_active = False
    subscriber.save()
    messages.info(request, "You've been unsubscribed. Sorry to see you go!")
    return redirect("home")


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
def register(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = RegistrationForm()
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                "Account created! Welcome to Inkwell. "
                "Verify your email to unlock everything.",
            )
            login(request, user)
            return redirect("send_verification")
    return render(request, "core/auth/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = LoginForm()
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            next_url = request.GET.get("next")
            return redirect(next_url or "home")
    return render(request, "core/auth/login.html", {"form": form})


def logout_view(request):
    logout(request)
    messages.info(request, "You've been signed out. See you soon!")
    return redirect("home")


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------
def _verification_token(user):
    return default_token_generator.make_token(user)


@login_required
def send_verification_email(request):
    profile = request.user.profile
    if profile.email_verified:
        messages.info(request, "Your email is already verified.")
        return redirect("profile_edit")

    if settings.DEFAULT_FROM_EMAIL and settings.EMAIL_BACKEND and "locmem" not in settings.EMAIL_BACKEND and "console" not in settings.EMAIL_BACKEND:
        token = _verification_token(request.user)
        uid = urlsafe_base64_encode(force_bytes(request.user.pk))
        link = request.build_absolute_uri(
            reverse("verify_email", kwargs={"uidb64": uid, "token": token})
        )
        subject = "Verify your email — Inkwell"
        body = render_to_string("emails/verify_email.txt", {"user": request.user, "link": link})
        send_mail(subject, body, None, [request.user.email], fail_silently=True)
        messages.success(request, "Verification email sent. Check your inbox.")
    else:
        messages.warning(
            request,
            "Email sending is not configured in this environment, so your account is active without verification.",
        )
    return redirect("profile_edit")


def verify_email(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user and default_token_generator.check_token(user, token):
        user.profile.email_verified = True
        user.profile.save(update_fields=["email_verified"])
        messages.success(request, "Email verified successfully. Welcome aboard!")
        return redirect("profile_edit")
    messages.error(request, "The verification link is invalid or has expired.")
    return redirect("home")


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
def profile_detail(request, username):
    profile_user = get_object_or_404(
        User.objects.select_related("profile").prefetch_related("blogs__tags"),
        username=username,
    )
    published = (
        Blog.objects.published()
        .filter(author=profile_user)
        .with_relations()
        .with_counts()
    )
    paginator, page, query_string = _paginate(published, request, per_page=6)

    context = {
        "profile_user": profile_user,
        "profile": profile_user.profile,
        "blogs": page.object_list,
        "page_obj": page,
        "paginator": paginator,
        "query_string": query_string,
        "is_own": request.user.is_authenticated and request.user == profile_user,
        "is_following": (
            request.user.is_authenticated
            and profile_user.profile.followers.filter(pk=request.user.pk).exists()
        ),
    }
    return render(request, "core/profile_detail.html", context)


@login_required
def profile_edit(request):
    user_form = UserProfileForm(instance=request.user)
    profile_form = ProfileForm(instance=request.user.profile)
    password_form = ChangePasswordForm(request.user)

    if request.method == "POST":
        action = request.POST.get("action", "profile")
        if action == "password":
            password_form = ChangePasswordForm(request.user, request.POST)
            if password_form.is_valid():
                password_form.save()
                messages.success(request, "Password changed. Please log in again.")
                return redirect("login")
        else:
            user_form = UserProfileForm(request.POST, instance=request.user)
            profile_form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)
            if user_form.is_valid() and profile_form.is_valid():
                user_form.save()
                profile_form.save()
                messages.success(request, "Profile updated successfully.")
                return redirect("profile_edit")

    context = {
        "user_form": user_form,
        "profile_form": profile_form,
        "password_form": password_form,
    }
    return render(request, "core/profile_edit.html", context)


@login_required
def saved_articles(request):
    blogs = request.user.bookmarked_blogs.with_relations().with_counts()
    paginator, page, query_string = _paginate(blogs, request)
    context = {"blogs": page.object_list, "page_obj": page, "paginator": paginator, "query_string": query_string}
    return render(request, "core/saved_articles.html", context)


# ---------------------------------------------------------------------------
# Blog authoring
# ---------------------------------------------------------------------------
@login_required
def blog_create(request):
    form = BlogForm()
    if request.method == "POST":
        form = BlogForm(request.POST, request.FILES)
        if form.is_valid():
            blog = form.save(commit=False)
            blog.author = request.user
            if request.POST.get("save_draft"):
                blog.status = Blog.Status.DRAFT
                blog.published_at = None
            elif request.user.is_staff:
                blog.status = form.cleaned_data.get("status", Blog.Status.DRAFT)
                if blog.status == Blog.Status.PUBLISHED and not blog.published_at:
                    blog.published_at = timezone.now()
            else:
                # Regular authors always submit for review.
                blog.status = Blog.Status.DRAFT
                blog.published_at = None
            blog.save()
            form.save_m2m()
            form._sync_tags(blog)
            messages.success(
                request,
                "Your post was saved."
                if blog.status == Blog.Status.DRAFT
                else "Your post has been published.",
            )
            return redirect("my_blogs")
    context = {"form": form, "title": "Write a new story", "is_edit": False}
    return render(request, "core/blog_editor.html", context)


@login_required
def blog_edit(request, slug):
    blog = get_object_or_404(Blog, slug=slug)
    if blog.author != request.user and not request.user.is_staff:
        raise PermissionDenied

    initial = {"tags_input": ", ".join(blog.tags.values_list("name", flat=True))}
    form = BlogForm(instance=blog, initial=initial)
    if request.method == "POST":
        form = BlogForm(request.POST, request.FILES, instance=blog, initial=initial)
        if form.is_valid():
            blog = form.save(commit=False)
            if request.POST.get("save_draft") or (
                not request.user.is_staff and blog.status == Blog.Status.PUBLISHED
            ):
                blog.status = Blog.Status.DRAFT
                blog.published_at = None
            blog.save()
            form.save_m2m()
            form._sync_tags(blog)
            messages.success(request, "Post updated.")
            return redirect("blog_edit", slug=blog.slug)
    context = {"form": form, "title": "Edit story", "is_edit": True, "blog": blog}
    return render(request, "core/blog_editor.html", context)


@login_required
def autosave_draft(request, slug):
    blog = get_object_or_404(Blog, slug=slug)
    if blog.author != request.user and not request.user.is_staff:
        return JsonResponse({"error": "Forbidden"}, status=403)
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    data = json.loads(request.body)
    blog.title = data.get("title", blog.title)
    blog.content = data.get("content", blog.content)
    blog.excerpt = data.get("excerpt", blog.excerpt)
    blog.updated_at = timezone.now()
    blog.save()
    return JsonResponse({"ok": True, "saved_at": blog.updated_at.isoformat()})


@login_required
def upload_image(request):
    """Handle image uploads from the editor (drag & drop / pasted)."""
    if request.method != "POST" or "image" not in request.FILES:
        return JsonResponse({"error": "No image provided"}, status=400)
    from .validators import validate_cover_image

    image = request.FILES["image"]
    try:
        validate_cover_image(image)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    from .models import Blog  # local import avoids circulars

    temp = Blog(title="__upload__")
    temp.author = request.user
    temp.status = Blog.Status.DRAFT
    temp.save()
    temp.cover_image = image
    temp.save(update_fields=["cover_image"])
    url = temp.cover_image.url
    temp.delete()  # keep only the uploaded file on disk
    return JsonResponse({"url": url})


@login_required
def my_blogs(request):
    blogs = (
        Blog.objects.filter(author=request.user)
        .with_relations()
        .order_by("-updated_at")
    )
    drafts = [b for b in blogs if b.status == Blog.Status.DRAFT]
    scheduled = [b for b in blogs if b.status == Blog.Status.PUBLISHED and b.published_at and b.published_at > timezone.now()]
    published = [b for b in blogs if b.status == Blog.Status.PUBLISHED and b not in scheduled]
    context = {"drafts": drafts, "published": published, "scheduled": scheduled}
    return render(request, "core/my_blogs.html", context)


@login_required
def delete_blog(request, pk):
    blog = get_object_or_404(Blog, pk=pk)
    if blog.author != request.user and not request.user.is_staff:
        raise PermissionDenied
    if request.method == "POST":
        blog.delete()
        messages.success(request, "Post deleted.")
        return redirect("my_blogs")
    return render(request, "core/confirm_delete.html", {"blog": blog})


# ---------------------------------------------------------------------------
# Moderation (staff only)
# ---------------------------------------------------------------------------
def _staff_required(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        messages.error(request, "You don't have permission to do that.")
        return False
    return True


@login_required
def pending_blogs(request):
    if not request.user.is_staff:
        raise PermissionDenied
    pending = (
        Blog.objects.filter(status=Blog.Status.DRAFT)
        .with_relations()
        .order_by("-created_at")
    )
    context = {"blogs": pending}
    return render(request, "core/pending.html", context)


@login_required
def approve_blog(request, pk):
    if not _staff_required(request):
        return redirect("home")
    blog = get_object_or_404(Blog, pk=pk)
    blog.status = Blog.Status.PUBLISHED
    if not blog.published_at:
        blog.published_at = timezone.now()
    blog.save()
    messages.success(request, f'"{blog.title}" is now live.')
    return redirect("pending")


@login_required
def feature_blog(request, pk):
    if not _staff_required(request):
        return redirect("home")
    blog = get_object_or_404(Blog, pk=pk)
    blog.is_featured = not blog.is_featured
    blog.save()
    messages.success(request, "Featured status toggled.")
    return redirect(request.META.get("HTTP_REFERER", "blogs"))


# ---------------------------------------------------------------------------
# Authors
# ---------------------------------------------------------------------------
def authors_page(request):
    authors = (
        User.objects.select_related("profile")
        .annotate(
            published_count=Count(
                "blogs",
                filter=Q(
                    blogs__status=Blog.Status.PUBLISHED,
                    blogs__published_at__lte=timezone.now(),
                ),
            ),
            total_views=Sum("blogs__view_count"),
        )
        .filter(published_count__gt=0)
        .order_by("-published_count")
    )
    context = {"authors": authors}
    return render(request, "core/authors.html", context)


def handler404_view(request, exception):
    return render(request, "core/404.html", status=404)
