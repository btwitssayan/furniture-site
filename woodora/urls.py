from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "WOODORA Admin"
admin.site.site_title = "WOODORA Admin"
admin.site.index_title = "Catalogue management"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("catalog.urls")),
]
