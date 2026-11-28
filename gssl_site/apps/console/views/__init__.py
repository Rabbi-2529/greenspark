"""Console views, grouped by what they are for."""

from .auth import (
    ConsoleLoginView,
    ConsoleLogoutView,
    ConsolePasswordChangeView,
    StaffPasswordView,
)
from .page import PageDetailView
from .crud import (
    ModuleDataView,
    ModuleDeleteView,
    ModuleDetailView,
    ModuleEditView,
    ModuleListView,
    ModulePublishView,
    ModuleReorderView,
)
from .dashboard import DashboardView

__all__ = [
    "PageDetailView",
    "ConsoleLoginView",
    "ConsoleLogoutView",
    "ConsolePasswordChangeView",
    "DashboardView",
    "ModuleDataView",
    "ModuleDeleteView",
    "ModuleDetailView",
    "ModuleEditView",
    "ModuleListView",
    "ModulePublishView",
    "ModuleReorderView",
    "StaffPasswordView",
]
