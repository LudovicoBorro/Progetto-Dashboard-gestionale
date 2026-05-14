from UI.controllers.base_controller import BaseController
from UI.views.project_detail_view import ProjectDetailView
from data.repositories.project_repository import ProjectRepository
from data.database import get_session
from UI.services.project_service import ProjectService
import flet as ft
import uuid

class DashboardController(BaseController):

    def __init__(self, view):
        super().__init__(view)

    def get_projects(self):
        """
        Recupera i progetti dal db.
        """
        projects = ProjectService.get_all_projects()

        return projects

    def get_project_by_id(self, project_id: str):
        """
        Recupera il progetto dal database.
        """
        project = ProjectService.get_project_by_id(uuid.UUID(project_id))

        return project

    def open_project(self, project_id):
        """
        Naviga alla vista dettaglio del progetto.
        """
        self.view.page.go(f"/project_details?id={project_id}")

        print(f"Apertura progetto {project_id}")
