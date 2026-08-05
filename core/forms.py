"""Form validation for every user-facing workflow."""

from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Blog, Category, Comment, ContactMessage, NewsletterSubscriber, Profile, Tag
from .validators import validate_cover_image


class StyleMixin:
    """Apply a shared CSS class to rendered widgets."""

    widget_class = "form-control"

    def _style(self):
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", self.widget_class)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
class RegistrationForm(StyleMixin, UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"placeholder": "you@example.com"}),
    )
    first_name = forms.CharField(
        required=False, max_length=150, widget=forms.TextInput(attrs={"placeholder": "First name"})
    )
    last_name = forms.CharField(
        required=False, max_length=150, widget=forms.TextInput(attrs={"placeholder": "Last name"})
    )

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")
        if commit:
            user.save()
        return user


class LoginForm(StyleMixin, AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"placeholder": "Username or email"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "Your password"}))


class ForgotPasswordForm(StyleMixin, PasswordResetForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"placeholder": "you@example.com"}))


class ResetPasswordConfirmForm(StyleMixin, SetPasswordForm):
    pass


class ChangePasswordForm(StyleMixin, PasswordChangeForm):
    pass


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
class ProfileForm(StyleMixin, forms.ModelForm):
    website = forms.URLField(required=False, widget=forms.URLInput(attrs={"placeholder": "https://"}))
    avatar = forms.ImageField(required=False, validators=[validate_cover_image])

    class Meta:
        model = Profile
        fields = (
            "avatar",
            "bio",
            "location",
            "website",
            "twitter",
            "github",
            "linkedin",
        )


class UserProfileForm(StyleMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")


# ---------------------------------------------------------------------------
# Blog
# ---------------------------------------------------------------------------
class BlogForm(StyleMixin, forms.ModelForm):
    tags_input = forms.CharField(
        required=False,
        label="Tags",
        help_text="Comma separated, e.g. python, django, web",
    )
    cover_image = forms.ImageField(
        required=False,
        label="Featured image",
        validators=[validate_cover_image],
    )

    class Meta:
        model = Blog
        fields = (
            "title",
            "content",
            "excerpt",
            "cover_image",
            "cover_alt",
            "category",
            "status",
            "published_at",
            "seo_title",
            "seo_description",
        )
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "A compelling title…"}),
            "content": forms.Textarea(attrs={"rows": 18, "placeholder": "Write in Markdown…"}),
            "excerpt": forms.Textarea(attrs={"rows": 3}),
            "published_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
        }
        help_texts = {
            "status": "Draft: private. Published: live (or scheduled if you pick a future date).",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].required = False
        self.fields["category"].empty_label = "No category"

    def clean_tags_input(self):
        raw = self.cleaned_data.get("tags_input", "")
        return [t.strip() for t in raw.split(",") if t.strip()]

    def clean_published_at(self):
        value = self.cleaned_data.get("published_at")
        status = self.cleaned_data.get("status")
        if status == Blog.Status.PUBLISHED and value and value > timezone.now() + timezone.timedelta(days=365):
            raise forms.ValidationError("Scheduled publish date is too far in the future.")
        return value

    def save(self, commit=True):
        blog = super().save(commit=False)
        blog.status = self.cleaned_data.get("status", Blog.Status.DRAFT)
        if blog.status == Blog.Status.PUBLISHED and not blog.published_at:
            blog.published_at = timezone.now()
        if commit:
            blog.save()
            self.save_m2m()
            self._sync_tags(blog)
        return blog

    def _sync_tags(self, blog):
        tag_names = self.cleaned_data.get("tags_input", [])
        tags = []
        for name in tag_names:
            tag, _ = Tag.objects.get_or_create(name=name)
            tags.append(tag)
        blog.tags.set(tags)


class BlogSearchForm(forms.Form):
    q = forms.CharField(required=False, max_length=200)
    category = forms.ModelChoiceField(queryset=Category.objects.all(), required=False)
    tag = forms.ModelChoiceField(queryset=Tag.objects.all(), required=False)
    author = forms.CharField(required=False, max_length=100)
    sort = forms.ChoiceField(
        required=False,
        choices=(
            ("newest", "Newest"),
            ("oldest", "Oldest"),
            ("popular", "Most viewed"),
            ("liked", "Most liked"),
        ),
    )


# ---------------------------------------------------------------------------
# Engagement
# ---------------------------------------------------------------------------
class CommentForm(StyleMixin, forms.ModelForm):
    content = forms.CharField(
        label="Comment",
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Share your thoughts…"}),
        max_length=2000,
    )

    class Meta:
        model = Comment
        fields = ("content",)


class ContactForm(StyleMixin, forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ("name", "email", "subject", "message")
        widgets = {
            "message": forms.Textarea(attrs={"rows": 6, "placeholder": "How can we help?"}),
        }


class NewsletterForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Enter your email",
                "class": "form-control",
                "aria-label": "Email address",
            }
        )
    )

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if NewsletterSubscriber.objects.filter(email=email, is_active=True).exists():
            raise forms.ValidationError("You're already subscribed.")
        return email
