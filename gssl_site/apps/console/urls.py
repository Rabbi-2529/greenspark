"""
Console URLs.

Six generic routes cover every registered module, so adding a content model in
a later phase adds no URL. ``<slug>`` is matched against the registry and a
slug that is not registered answers 404.
"""

from django.urls import path

from . import views

app_name = "console"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),

    # Signing in and out.
    path("sign-in/", views.ConsoleLoginView.as_view(), name="login"),
    path("sign-out/", views.ConsoleLogoutView.as_view(), name="logout"),
    path("password/", views.ConsolePasswordChangeView.as_view(), name="password_change"),
    path("staff/<int:pk>/password/", views.StaffPasswordView.as_view(), name="staff_password"),

    # Every module, through the same six views.
    path("<slug:slug>/", views.ModuleListView.as_view(), name="list"),
    path("<slug:slug>/data/", views.ModuleDataView.as_view(), name="data"),
    path("<slug:slug>/new/", views.ModuleEditView.as_view(), name="create"),
    path("<slug:slug>/reorder/", views.ModuleReorderView.as_view(), name="reorder"),
    path("<slug:slug>/<int:pk>/", views.ModuleDetailView.as_view(), name="detail"),
    path("<slug:slug>/<int:pk>/edit/", views.ModuleEditView.as_view(), name="edit"),
    path("<slug:slug>/<int:pk>/delete/", views.ModuleDeleteView.as_view(), name="delete"),
    path("<slug:slug>/<int:pk>/publish/", views.ModulePublishView.as_view(), name="publish"),
]
