from django.contrib import admin
from django.templatetags.static import static
from django.urls import include, path
from django.views.generic.base import RedirectView

admin.site.site_header = "WOODORA Admin"
admin.site.site_title = "WOODORA Admin"
admin.site.index_title = "Catalogue management"

urlpatterns = [
    # Browsers request /favicon.ico at the site root regardless of the <link>
    # tags, and static files are served from /static/. Point them at the real
    # file rather than letting it 404 on every page load.
    path(
        "favicon.ico",
        RedirectView.as_view(url=static("icons/favicon.ico"), permanent=True),
    ),
    path("admin/", admin.site.urls),
    path("", include("catalog.urls")),
]
