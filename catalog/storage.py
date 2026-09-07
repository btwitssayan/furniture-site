"""Uploading product images to Supabase Storage.

The schema keeps `image_url TEXT` as the single source of truth for an image.
Uploading through the admin pushes the file to a Supabase Storage bucket and
returns its public URL, which is then written into that column -- so uploaded
images and externally hosted ones (the seeded Unsplash URLs) are the same kind
of value and nothing downstream has to care which is which.

Supabase Storage speaks S3, so django-storages' S3Storage backend does the
transfer; only the public-URL shape is Supabase-specific.
"""

import mimetypes
import posixpath
import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage

#: Extensions we accept. Kept deliberately narrow -- these are public images.
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif"}

#: Supabase's own default object size cap on the free tier.
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


def is_enabled():
    """True when every Supabase Storage setting needed to upload is present."""
    return bool(getattr(settings, "SUPABASE_STORAGE_ENABLED", False))


def public_url(key):
    """Public URL for an object in the configured bucket.

    Supabase serves public buckets from
    <project>/storage/v1/object/public/<bucket>/<key>.
    """
    base = settings.SUPABASE_URL.rstrip("/")
    return f"{base}/storage/v1/object/public/{settings.SUPABASE_BUCKET}/{key}"


def build_key(filename, prefix="products"):
    """Collision-proof object key that keeps the original name readable."""
    stem = Path(filename).stem[:60].strip().replace(" ", "-") or "image"
    suffix = Path(filename).suffix.lower()
    return posixpath.join(prefix, f"{stem}-{uuid.uuid4().hex[:8]}{suffix}")


def validate(uploaded_file):
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"{suffix or 'That file type'} is not allowed. "
            f"Use one of: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )
    if uploaded_file.size > MAX_UPLOAD_BYTES:
        raise ValidationError(
            f"File is {uploaded_file.size / 1024 / 1024:.1f}MB; "
            f"the limit is {MAX_UPLOAD_BYTES // 1024 // 1024}MB."
        )


def upload_image(uploaded_file, prefix="products"):
    """Send an uploaded file to Supabase Storage; return its public URL.

    Raises ValidationError when Storage is not configured or the file is
    rejected, so the admin surfaces the reason on the form rather than 500ing.
    """
    if not is_enabled():
        raise ValidationError(
            "Supabase Storage is not configured. Set SUPABASE_URL, "
            "SUPABASE_S3_ENDPOINT and the S3 key pair in .env, or paste an "
            "image URL instead of uploading a file."
        )

    validate(uploaded_file)

    key = build_key(uploaded_file.name, prefix)
    content_type = (
        getattr(uploaded_file, "content_type", None)
        or mimetypes.guess_type(uploaded_file.name)[0]
        or "application/octet-stream"
    )
    uploaded_file.content_type = content_type

    stored_key = default_storage.save(key, uploaded_file)
    return public_url(stored_key)
