from UI.views.base_view import BaseView
from data.models.project import Project
from UI.controllers.project_controller import ProjectController
from UI.widgets.error_alert import ErrorAlert
import flet as ft

class ProjectDetailView(BaseView):
    def __init__(self, page: ft.Page, project: Project):
        super().__init__(route="/project_details")
        self.project = project
        self._page_ref = page

    def build_view(self):
        """
        Costruisce i controlli specifici della vista dettaglio.
        """
        if not self.controller:
            return

        # ---------------- DIALOGS ----------------
        self.info_edit_dialog = ErrorAlert(
            error_message="Il file Excel verrà aperto alla chiusura di questo pop-up.\n\n1. Apporta le modifiche desiderate\n2. SALVA il file in Excel\n3. Torna qui per abilitare il tasto 'Importa Dati'",
            title="Istruzioni Modifica",
            actions=[
                ft.TextButton("Ho capito", on_click=self._open_excel_and_close_dialog)
            ],
        )

        self.confirm_dialog = ErrorAlert(
            error_message="Attenzione: Questa operazione sovrascriverà tutti i dati e le attività attuali del progetto con quelli del file Excel. Vuoi procedere?",
            title="Conferma Importazione",
            actions=[
                ft.TextButton("Annulla", on_click=self._close_confirm_dialog),
                ft.TextButton("Sì, Importa tutto", on_click=self.controller.import_project_data, style=ft.ButtonStyle(color=ft.Colors.RED))
            ],
        )

        # ---------------- TOP BAR ----------------
        self.btn_import = ft.ElevatedButton(
            "Importa Dati",
            icon=ft.Icons.UPLOAD_FILE,
            bgcolor=ft.Colors.GREEN_800,
            color=ft.Colors.WHITE,
            disabled=True,
            on_click=self.controller.confirm_import
        )

        top_bar = ft.Container(
            padding=20,
            bgcolor=ft.Colors.with_opacity(0.03, ft.Colors.WHITE),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text(self.project.name, size=24, weight=ft.FontWeight.BOLD),
                    ft.Row(
                        spacing=15,
                        controls=[
                            ft.TextButton("Torna indietro", icon=ft.Icons.ARROW_BACK, on_click=self.controller.go_dashboard),
                            ft.VerticalDivider(width=1, color=ft.Colors.WHITE24),
                            ft.ElevatedButton(
                                "Modifica Excel",
                                icon=ft.Icons.EDIT_NOTE,
                                on_click=self.controller.create_info_dialog
                            ),
                            self.btn_import,
                            ft.VerticalDivider(width=1, color=ft.Colors.WHITE24),
                            ft.FilledButton("Vai alla schedulazione", icon=ft.Icons.PLAY_ARROW, on_click=self.controller.go_scheduling_view)
                        ]
                    )
                ]
            )
        )

        # Usiamo il layout base
        self.set_content(
            controls=[
                top_bar,
                self._project_stats_card(),
                self._activities_section()
            ]
        )

    def _close_info_dialog(self, e=None):
        self.info_edit_dialog.open = False
        if self._page_ref:
            if hasattr(self._page_ref, 'close'):
                self._page_ref.close(self.info_edit_dialog)
            else:
                self._page_ref.update()

    def _close_confirm_dialog(self, e=None):
        self.confirm_dialog.open = False
        if self._page_ref:
            if hasattr(self._page_ref, 'close'):
                self._page_ref.close(self.confirm_dialog)
            else:
                self._page_ref.update()

    def _activities_section(self):
        activities = self.controller.get_activities()

        if not activities:
            return ft.Column(
                controls=[
                    ft.Text("Attività del progetto", size=18, weight=ft.FontWeight.BOLD),
                    ft.Container(
                        padding=20,
                        border_radius=12,
                        bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.WHITE),
                        content=ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Icon(ft.Icons.INFO_OUTLINE, size=40, color=ft.Colors.WHITE38),
                                ft.Text("Nessuna attività importata.", color=ft.Colors.WHITE70),
                                ft.Text("Clicca 'Modifica Excel' e poi 'Importa Dati'.", color=ft.Colors.WHITE38, size=12),
                            ]
                        )
                    )
                ]
            )

        # Costruiamo la tabella delle attività
        rows = []
        for act in activities:
            cfg = act.activity_config_json or {}
            duration = cfg.get("duration", "-")
            rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(act.id_for_project))),
                    ft.DataCell(ft.Text(act.name)),
                    ft.DataCell(ft.Text(str(duration))),
                ])
            )


        return ft.Column(
            spacing=10,
            controls=[
                ft.Text("Attività del progetto", size=18, weight=ft.FontWeight.BOLD),
                ft.Text(f"{len(activities)} attività importate", size=12, color=ft.Colors.WHITE60),
                ft.Container(
                    border_radius=12,
                    bgcolor=ft.Colors.with_opacity(0.03, ft.Colors.WHITE),
                    padding=10,
                    content=ft.DataTable(
                        columns=[
                            ft.DataColumn(ft.Text("ID")),
                            ft.DataColumn(ft.Text("Nome")),
                            ft.DataColumn(ft.Text("Durata")),
                        ],
                        rows=rows,
                    )
                )
            ]
        )


    def _project_stats_card(self):
        return ft.Container(
            padding=15,
            border_radius=12,
            bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.WHITE),
            content=ft.Column(
                spacing=15,
                controls=[
                    ft.Text("Statistiche del progetto", size=18, weight=ft.FontWeight.BOLD),
                    ft.Row(
                        spacing=20,
                        controls=[
                            ft.Column(
                                controls=[
                                    ft.Text("Budget iniziale", size=12, color=ft.Colors.WHITE70),
                                    ft.Text(f"€{(self.project.initial_budget or 0.0):,.2f}", size=22, weight=ft.FontWeight.BOLD)
                                ]
                            ),
                            ft.Column(
                                controls=[
                                    ft.Text("Budget finale", size=12, color=ft.Colors.WHITE70),
                                    ft.Text(f"€{(self.project.final_budget or 0.0):,.2f}", size=22, weight=ft.FontWeight.BOLD)
                                ]
                            )
                        ]
                    )
                ]
            )
        )

    def _open_excel_and_close_dialog(self, e):
        self.controller.open_excel_file(e)
        self._close_info_dialog(e)


