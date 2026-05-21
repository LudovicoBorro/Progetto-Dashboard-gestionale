import flet as ft
from UI.views.base_view import BaseView
from UI.widgets.project_card import ProjectCard

class DashboardView(BaseView):
    def __init__(self, page: ft.Page):
        super().__init__(route="/")
        self._page_ref = page

    def build_view(self):
        """
        Costruisce i controlli specifici della Dashboard.
        """
        if not self.controller:
            return

        projects = self.controller.get_projects()

        def status_label(project):
            status = project.status
            return str(getattr(status, "value", status)).lower()

        # ---------------- HEADER ----------------
        header = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Column(
                    spacing=5,
                    controls=[
                        ft.Text("Dashboard Gestionale Progetti", size=30, weight=ft.FontWeight.BOLD),
                        ft.Text("RCPSP / RCPSP-MAX Scheduling System", size=14, color=ft.Colors.WHITE70)
                    ]
                ),
                ft.ElevatedButton(
                    content=ft.Text("Nuovo Progetto"),
                    icon=ft.Icons.ADD,
                    on_click=self.controller.go_new_project
                )
            ]
        )

        # ---------------- STATS ----------------
        stats = ft.Container(
            bgcolor=ft.Colors.with_opacity(0.03, ft.Colors.WHITE),
            border_radius=12,
            padding=20,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
                controls=[
                    self._stat_card("Totale Progetti", len(projects)),
                    self._stat_card("Completati", len([p for p in projects if "complet" in status_label(p)])),
                    self._stat_card("Schedulati", len([p for p in projects if "schedulat" in status_label(p) and "da sched" not in status_label(p)])),
                    self._stat_card("Da schedulare", len([p for p in projects if "da sched" in status_label(p)])),
                    self._stat_card("Sospesi", len([p for p in projects if "sospes" in status_label(p)])),
                ]
            )
        )

        # ---------------- PROJECT GRID ----------------
        project_grid = ft.ResponsiveRow(
            spacing=15,
            run_spacing=15,
            controls=[
                ProjectCard(
                    project=p, on_open=self.controller.go_project_details, on_open_gantt=self.controller.go_gantt, 
                    suspend_project=self.controller.suspend_project, resume_project=self.controller.resume_project, 
                    delete_project=self.controller.delete_project).build()
                for p in projects
            ]
        )

        # Impostiamo il contenuto usando il layout base
        self.set_content(
            controls=[
                header,
                ft.Divider(),
                stats,
                ft.Divider(),
                ft.Text("Progetti", size=22, weight=ft.FontWeight.BOLD),
                project_grid
            ]
        )

    def _stat_card(self, title: str, value: int):
        return ft.Container(
            padding=15,
            border_radius=12,
            bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.WHITE),
            content=ft.Column(
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(title, size=12, color=ft.Colors.WHITE70),
                    ft.Text(str(value), size=22, weight=ft.FontWeight.BOLD)
                ]
            )
        )
