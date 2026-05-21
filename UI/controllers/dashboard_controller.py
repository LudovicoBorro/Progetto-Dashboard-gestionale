from UI.controllers.base_controller import BaseController
from UI.views.project_detail_view import ProjectDetailView
from data.database import get_session
from UI.services.project_service import ProjectService
from data.models.project import ProjectStatus
import flet as ft
import uuid
from UI.widgets.error_alert import ErrorAlert
import asyncio

class DashboardController(BaseController):

    def __init__(self, view):
        super().__init__(view)

    def get_projects(self):
        """
        Recupera i progetti dal db.
        """
        projects = ProjectService.get_all_projects()

        return projects

    def get_project_by_id(self, project_id):
        """
        Recupera il progetto dal database.
        """
        project = ProjectService.get_project_by_id(uuid.UUID(project_id))

        return project

    def suspend_project(self, project_id):
        """
        Sospende il progetto.
        """
        project = ProjectService.get_project_by_id(project_id)

        if project:
            project.status = ProjectStatus.SUSPENDED
            ProjectService.update_project_status(project_id, ProjectStatus.SUSPENDED)

            print(f"Progetto {project_id} sospeso")
    
    def resume_project(self, project_id):
        """
        Riprende il progetto.
        """
        project = ProjectService.get_project_by_id(project_id)

        if project:
            project.status = ProjectStatus.NOTSCHEDULED
            ProjectService.update_project_status(project_id, ProjectStatus.NOTSCHEDULED)

            print(f"Progetto {project_id} ripreso")
    
    async def delete_project(self, project_id):
        """
        Elimina il progetto.
        """
        confirm_dialog = ErrorAlert(
            error_message="Sei sicuro di voler eliminare il progetto? "
            "\nQuesta operazione non può essere annullata.",
            title="Conferma eliminazione",
            actions=[
                ft.TextButton("Conferma",
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=10),
                                color=ft.Colors.RED, 
                                bgcolor=ft.Colors.RED_100,
                            ),
                            on_click=lambda e: self.delete_project_confirmed(project_id, confirm_dialog)),
                ft.TextButton("Annulla", on_click=lambda e: self.close_dialog(confirm_dialog))
            ]
        )

        await asyncio.sleep(0.5)

        self.view._page_ref.dialog = confirm_dialog
        confirm_dialog.open = True
        self.view._page_ref.update()

    def delete_project_confirmed(self, project_id, confirm_dialog):
        ProjectService.delete_project(project_id)
        self.close_dialog(confirm_dialog)

        print(f"Progetto {project_id} eliminato")

    def close_dialog(self, dialog):
        dialog.open = False
        self.view._page_ref.update()