import flet as ft
from UI.services.project_service import ProjectService
import uuid

class BaseController:
    """
    Classe base per tutti i controller della UI.
    Contiene la logica di navigazione condivisa (sidebar, menu, etc.).
    """
    def __init__(self, view):
        self.view = view

    def go_dashboard(self, e):
        """Naviga alla dashboard."""
        self.view.page.go("/")

    def go_new_project(self, e):
        """Naviga alla creazione di un nuovo progetto."""
        print("Navigazione a Nuovo Progetto")
        self.view.page.go("/new_project")

    def go_project_details(self, project_id):
        """Naviga alla vista dettaglio del progetto."""
        self.view.page.go(f"/project_details?id={project_id}")

        print(f"Apertura progetto {project_id}")

    def go_gantt(self, project_id):
        """Naviga alla vista Gantt del progetto corrente."""
        self.view.page.go(f"/gantt?id={project_id}")

        print(f"Navigazione a Gantt per il progetto {project_id}")

    def go_stats(self, e):
        """Naviga alla vista statistiche."""
        print("Navigazione a Statistiche")

    def go_settings(self, e):
        """Naviga alle impostazioni."""
        print("Navigazione a Impostazioni")

    def go_scheduling(self, project_id):
        """Naviga alla vista scheduling del progetto."""
        self.view.page.go(f"/scheduling?id={project_id}")

        print(f"Apertura scheduling progetto {project_id}")
