"""Admin forms that add Supabase Storage uploads on top of the URL columns."""

from django import forms

from . import storage
from .models import Category, Collection, ProductImage


class _UploadToUrlForm(forms.ModelForm):
    """Base for models whose image is stored as a URL in a text column.

    Adds an `upload` file field. When a file is given it goes to Supabase
    Storage and the resulting public URL is written into the URL field, so
    the column keeps being the one source of truth.
    """

    url_field = None  # subclasses set this

    upload = forms.FileField(
        required=False,
        label="Upload image",
        help_text="Optional. Uploads to Supabase Storage and fills in the URL below.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The URL can arrive either by upload or by hand, so it cannot be
        # required at the form level; clean() enforces that one of them is set.
        self.fields[self.url_field].required = False
        if not storage.is_enabled():
            self.fields["upload"].disabled = True
            self.fields["upload"].help_text = (
                "Supabase Storage is not configured (see .env.example). "
                "Paste an image URL instead."
            )

    def clean(self):
        cleaned = super().clean()
        upload = cleaned.get("upload")
        url = cleaned.get(self.url_field)

        if upload:
            # storage.upload_image raises ValidationError with a readable
            # message, which lands on the upload field rather than as a 500.
            try:
                cleaned[self.url_field] = storage.upload_image(upload)
            except forms.ValidationError as exc:
                self.add_error("upload", exc)
        elif not url and self._url_is_required():
            self.add_error(
                self.url_field, "Upload a file or paste an image URL."
            )
        return cleaned

    def _url_is_required(self):
        """Skip the check on blank extra inline rows the admin never saves."""
        if not self.instance.pk and not self.has_changed():
            return False
        return True

    def save(self, commit=True):
        instance = super().save(commit=False)
        url = self.cleaned_data.get(self.url_field)
        if url:
            setattr(instance, self.url_field, url)
        if commit:
            instance.save()
        return instance


class ProductImageForm(_UploadToUrlForm):
    url_field = "image_url"

    class Meta:
        model = ProductImage
        fields = "__all__"


class CategoryForm(_UploadToUrlForm):
    url_field = "image_url"

    class Meta:
        model = Category
        fields = "__all__"

    def _url_is_required(self):
        return False  # a category may legitimately have no banner


class CollectionForm(_UploadToUrlForm):
    url_field = "image_url"

    class Meta:
        model = Collection
        fields = "__all__"

    def _url_is_required(self):
        return False
