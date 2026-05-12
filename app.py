import flet as ft

from UI.views.dashboard_view import DashboardView
from UI.controllers.dashboard_controller import DashboardController

def main(page: ft.Page):

    dashboard = DashboardView(
        page,
        DashboardController()
    )

    dashboard.build()


ft.app(target=main)