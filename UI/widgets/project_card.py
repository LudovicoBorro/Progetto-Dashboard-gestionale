import flet as ft


class ProjectCard:

    def __init__(self, project, on_open):

        self.project = project
        self.on_open = on_open

    def _status_color(self, status: str):

        status = status.lower()

        if "complet" in status:
            return ft.Colors.GREEN
        elif "esec" in status:
            return ft.Colors.ORANGE
        elif "da sched" in status:
            return ft.Colors.RED
        else:
            return ft.Colors.BLUE

    def build(self):

        return ft.Container(
            width=320,
            padding=15,
            border_radius=15,
            bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.WHITE),
            border=ft.Border.all(0.5, ft.Colors.WHITE10),
            content=ft.Column(
                spacing=10,
                controls=[

                    ft.Text(
                        self.project.name,
                        size=18,
                        weight=ft.FontWeight.BOLD
                    ),

                    ft.Container(
                        padding=ft.Padding(10, 4, 10, 4),
                        border_radius=20,
                        bgcolor=self._status_color(self.project.status),
                        content=ft.Text(
                            self.project.status,
                            size=12,
                            color=ft.Colors.WHITE
                        )
                    ),

                    ft.Divider(height=10),

                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[

                            ft.TextButton(
                                "Apri",
                                icon=ft.Icons.FOLDER_OPEN,
                                on_click=lambda e: self.on_open(self.project.id)
                            ),

                            ft.TextButton(
                                "Statistiche",
                                icon=ft.Icons.ANALYTICS,
                                on_click=lambda e: print("Statistiche")
                            )
                        ]
                    )
                ]
            )
        )