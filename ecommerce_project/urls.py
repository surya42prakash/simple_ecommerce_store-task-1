from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Simple Store Administration"
admin.site.site_title = "Simple Store Admin"
admin.site.index_title = "Manage products, orders and customers"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("store.urls")),
]

# Serve uploaded product images only during local development.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
