import flet as ft

from UI.controllers.dashboard_controller import DashboardController
from UI.widgets.project_card import ProjectCard
from UI.widgets.sidebar import Sidebar


class DashboardView:

    def __init__(self, page: ft.Page, controller: DashboardController):

        self.page = page
        self.controller = controller

        self.page.title = "Dashboard gestionale progetti"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.padding = 0

    def build(self):

        projects = self.controller.get_projects()

        sidebar = Sidebar(self.controller)

        # ---------------- HEADER ----------------
        header = ft.Container(
            padding=20,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[

                    ft.Column(
                        spacing=5,
                        controls=[
                            ft.Text(
                                "Dashboard Gestionale Progetti",
                                size=30,
                                weight=ft.FontWeight.BOLD
                            ),
                            ft.Text(
                                "RCPSP / RCPSP-MAX Scheduling System",
                                size=14,
                                color=ft.Colors.WHITE70
                            )
                        ]
                    ),

                    ft.ElevatedButton(
                        content=ft.Text("Nuovo Progetto"),
                        icon=ft.Icons.ADD,
                        on_click=self.controller.go_new_project
                    )
                ]
            )
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

                    self._stat_card(
                        "In Esecuzione",
                        len([p for p in projects if "esec" in p["status"].lower()])
                    ),

                    self._stat_card(
                        "Da schedulare",
                        len([p for p in projects if "sched" in p["status"].lower()])
                    ),
                ]
            )
        )

        # ---------------- PROJECT GRID ----------------
        project_grid = ft.ResponsiveRow(
            spacing=15,
            run_spacing=15,
            controls=[
                ProjectCard(
                    project=p,
                    on_open=self.controller.open_project
                ).build()
                for p in projects
            ]
        )

        # ---------------- MAIN CONTENT ----------------
        main_content = ft.Container(
            expand=True,
            padding=20,
            content=ft.Column(
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    header,
                    ft.Divider(),
                    stats,
                    ft.Divider(),

                    ft.Text(
                        "Progetti",
                        size=22,
                        weight=ft.FontWeight.BOLD
                    ),

                    project_grid
                ]
            )
        )

        # ---------------- FINAL LAYOUT ----------------
        layout = ft.Row(
            expand=True,
            controls=[
                sidebar,
                ft.VerticalDivider(width=1),
                main_content
            ]
        )

        self.page.add(layout)

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