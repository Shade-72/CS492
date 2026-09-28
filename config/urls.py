from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(pattern_name="accounts:dashboard"), name="home"),
    path("", include("accounts.urls")),
    path("", include("academics.urls")),
    path("", include("family_portal.urls")),
    path("", include("notices.urls")),
]
