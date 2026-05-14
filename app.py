from UI.views.scheduling_view import SchedulingView
import flet as ft
from UI.views.dashboard_view import DashboardView
from UI.views.project_detail_view import ProjectDetailView
from UI.controllers.dashboard_controller import DashboardController
from UI.controllers.project_controller import ProjectController
from UI.controllers.scheduling_controller import SchedulingController

def main(page: ft.Page):

    page.title = "Dashboard gestionale progetti"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0

    def route_change(e):
        troute = ft.TemplateRoute(page.route)
        page.views.clear()

        
        # Dashboard
        dashboard = DashboardView(page)
        dashboard_controller = DashboardController(dashboard)
        dashboard.controller = dashboard_controller
        page.views.append(dashboard)

        # Project Details
        if page.route.startswith("/project_details"):
            project_id = page.query.get("id")
            if project_id:
                project = dashboard_controller.get_project_by_id(project_id)
                project_view = ProjectDetailView(page, project)
                project_controller = ProjectController(project_view, project)
                project_view.controller = project_controller
                page.views.append(project_view)
        
        # Scheduling
        if page.route.startswith("/scheduling"):
            project_id = page.query.get("id")
            if project_id:
                project = dashboard_controller.get_project_by_id(project_id)
                project_view = SchedulingView(page, project)
                project_controller = SchedulingController(project_view, project)
                project_view.controller = project_controller
                page.views.append(project_view)

        page.update()

    def view_pop(e):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    
    # Inizializzazione manuale della prima route
    route_change(None) 

ft.run(main=main)