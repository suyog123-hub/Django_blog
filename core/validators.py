"""Shared validators used across forms."""

import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

ALLOWED_IMAGE_TYPES = (
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/avif",
)
MAX_IMAGE_SIZE_MB = 5

USERNAME_RE = re.compile(r"^[\w.@+-]+$")


def validate_cover_image(image):
    """Validate that an uploaded image is allowed and under the size cap."""
    if not image:
        return

    if hasattr(image, "content_type") and image.content_type not in ALLOWED_IMAGE_TYPES:
        raise ValidationError(
            _("Unsupported image type. Use JPEG, PNG, WebP, GIF or AVIF.")
        )

    if image.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise ValidationError(_("Image must be under %s MB.") % MAX_IMAGE_SIZE_MB)


def validate_username(value):
    if not USERNAME_RE.match(value):
        raise ValidationError(
            _("Username may only contain letters, numbers and @/./+/-/_ characters.")
        )
