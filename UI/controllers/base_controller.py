import flet as ft

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
        # self.view.page.go("/new_project")

    def go_gantt(self, e):
        """Naviga alla vista Gantt del progetto corrente."""
        project = getattr(self, "project", None)
        if not project and hasattr(self.view, "project"):
            project = self.view.project
            
        if project:
            print(f"Navigazione a Gantt per il progetto {project.id}")
            self.view.page.go(f"/gantt?id={project.id}")
        else:
            print("Errore: Nessun progetto in contesto per accedere al Gantt.")

    def go_stats(self, e):
        """Naviga alla vista statistiche."""
        print("Navigazione a Statistiche")

    def go_settings(self, e):
        """Naviga alle impostazioni."""
        print("Navigazione a Impostazioni")
