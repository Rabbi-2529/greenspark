"""Root URL configuration."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Our own admin panel. django.contrib.admin stays mounted below until the
    # console reaches parity, then comes out (see CMS-PLAN.md, Phase 10).
    path(settings.CONSOLE_URL, include("apps.console.urls")),
    path(settings.ADMIN_URL, admin.site.urls),
    path("", include("apps.website.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = "apps.website.views.page_not_found"
handler500 = "apps.website.views.server_error"
