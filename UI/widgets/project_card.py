import flet as ft
from data.models.project import ProjectStatus

class ProjectCard:

    def __init__(self, project, on_open, on_open_gantt, suspend_project, resume_project, delete_project):

        self.project = project
        self.on_open = on_open
        self.on_open_gantt = on_open_gantt
        self.suspend_project = suspend_project
        self.resume_project = resume_project
        self.delete_project = delete_project

    def _status_label(self):
        status = self.project.status
        return getattr(status, "value", status)

    def _status_color(self, status: str):

        status = str(status).lower()

        if "complet" in status:
            return ft.Colors.GREEN
        elif "da sched" in status:
            return ft.Colors.RED
        elif "schedulat" in status:
            return ft.Colors.BLUE
        elif "sospes" in status:
            return ft.Colors.ORANGE
        else:
            return ft.Colors.BLUE

    def build(self):
        status_label = self._status_label()

        itemsPopMenu = [
            ft.PopupMenuItem(
                content=ft.Text("Apri progetto"),
                on_click=lambda e: self.on_open(project_id=self.project.id)
            )
        ]
        if self.project.status in [ProjectStatus.NOTSCHEDULED, ProjectStatus.SUSPENDED]:
            itemsPopMenu.append(
                ft.PopupMenuItem(
                    content=ft.Text("Schedula progetto"),
                    on_click=lambda e: self.on_open(project_id=self.project.id)
                )
            )

        if self.project.status in [ProjectStatus.SCHEDULED, ProjectStatus.COMPLETED]:
            itemsPopMenu.append(
                ft.PopupMenuItem(
                    content=ft.Text("Apri gantt"),
                    on_click=lambda e: self.on_open_gantt(project_id=self.project.id)
                )
            )

        if self.project.status not in [ProjectStatus.SUSPENDED, ProjectStatus.COMPLETED, ProjectStatus.NOTSCHEDULED]:
            itemsPopMenu.append(
                ft.PopupMenuItem(
                    content=ft.Text("Sospendi progetto"),
                    on_click=lambda e: self.suspend_project(project_id=self.project.id)
                )
            )

        if self.project.status == ProjectStatus.SUSPENDED:
            itemsPopMenu.append(
                ft.PopupMenuItem(
                    content=ft.Text("Riprendi progetto"),
                    on_click=lambda e: self.resume_project(project_id=self.project.id)
                )
            )

        if self.project.status != ProjectStatus.COMPLETED:
            itemsPopMenu.append(
                ft.PopupMenuItem(
                    content=ft.Text("Elimina progetto", color=ft.Colors.RED),
                    on_click=lambda e: e.page.run_task(self.delete_project, self.project.id)
                )
            )

        return ft.Container(
            width=320,
            padding=15,
            border_radius=15,
            bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.WHITE),
            border=ft.Border.all(0.5, ft.Colors.WHITE10),
            content=ft.Column(
                spacing=10,
                controls=[

                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(
                                self.project.name,
                                size=18,
                                weight=ft.FontWeight.BOLD
                            ),
                            ft.PopupMenuButton(
                                icon=ft.Icons.MORE_VERT,
                                items=itemsPopMenu,
                            )
                        ]
                    ),

                    ft.Container(
                        padding=ft.Padding(10, 4, 10, 4),
                        border_radius=20,
                        bgcolor=self._status_color(status_label),
                        content=ft.Text(
                            status_label,
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
                                "Gantt",
                                icon=ft.Icons.TIMELINE,
                                on_click=lambda e: self.on_open_gantt(self.project.id)
                            )
                            if self.project.status == ProjectStatus.SCHEDULED or self.project.status == ProjectStatus.COMPLETED
                            else ft.Container(opacity=0)
                        ]
                    ),
                ]
            )
        )
