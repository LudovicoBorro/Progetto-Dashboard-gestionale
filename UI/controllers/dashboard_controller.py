import flet as ft

class DashboardController:

    def __init__(self):
        pass

    def get_projects(self):
        """
        Simula recupero progetti dal database.
        In futuro chiamerai repository/service.
        """

        return [
            {
                "id": 1,
                "name": "Progetto RCPSP Alpha",
                "status": "Completato"
            },
            {
                "id": 2,
                "name": "Progetto Produzione",
                "status": "In esecuzione"
            },
            {
                "id": 3,
                "name": "Project Scheduling Test",
                "status": "Da schedulare"
            }
        ]

    def open_project(self, project_id: int):
        """
        Qui in futuro:
        - caricherai il progetto
        - aprirai la project_detail_view
        """

        print(f"Apertura progetto {project_id}")

    def go_new_project(self, e):
        """
        Callback bottone nuovo progetto.
        """

        print("Creazione nuovo progetto")

    def go_dashboard(self, e):
        """
        Naviga alla dashboard.
        """
        pass

    def go_gantt(self, e):
        """
        Naviga alla vista Gantt.
        """
        pass

    def go_stats(self, e):
        """
        Naviga alla vista statistiche.
        """
        pass

    def go_settings(self, e):
        """
        Naviga alla vista impostazioni.
        """
        pass