import flet as ft


class Sidebar(ft.Container):

    def __init__(self, controller):
        super().__init__()

        self.controller = controller

        self.width = 260
        self.padding = 15
        self.bgcolor = ft.Colors.BLUE_GREY_900

        self.content = self._build()

    def _build(self):

        title = ft.Text(
            "RCPSP Manager",
            size=20,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.WHITE
        )

        subtitle = ft.Text(
            "Project Scheduler",
            size=12,
            color=ft.Colors.WHITE70
        )

        return ft.Column(
            controls=[

                ft.Container(
                    content=ft.Column([title, subtitle]),
                    padding=10
                ),

                ft.Divider(color=ft.Colors.WHITE24),

                self._nav_button(
                    icon=ft.Icons.DASHBOARD,
                    text="Home",
                    on_click=self.controller.go_dashboard
                ),

                self._nav_button(
                    icon=ft.Icons.ADD_BOX,
                    text="Nuovo Progetto",
                    on_click=self.controller.go_new_project
                ),

                self._nav_button(
                    icon=ft.Icons.TIMELINE,
                    text="Gantt",
                    on_click=self.controller.go_gantt
                ),

                self._nav_button(
                    icon=ft.Icons.ANALYTICS,
                    text="Statistiche",
                    on_click=self.controller.go_stats
                ),

                ft.Divider(color=ft.Colors.WHITE24),

                self._nav_button(
                    icon=ft.Icons.SETTINGS,
                    text="Impostazioni",
                    on_click=self.controller.go_settings
                ),
            ],
            spacing=10
        )

    def _nav_button(self, icon, text, on_click):

        return ft.TextButton(
            content=ft.Row(
                controls=[
                    ft.Icon(icon, color=ft.Colors.WHITE),
                    ft.Text(text, color=ft.Colors.WHITE)
                ]
            ),
            on_click=on_click,
            style=ft.ButtonStyle(
                alignment=ft.Alignment.CENTER_LEFT
            )
        )