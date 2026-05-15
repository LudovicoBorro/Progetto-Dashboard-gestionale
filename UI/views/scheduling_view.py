import flet as ft
from UI.views.base_view import BaseView
from data.models.project import Project

class SchedulingView(BaseView):

    def __init__(self, page: ft.Page, project: Project):
        super().__init__(route="/scheduling")
        self.project = project
        self._page_ref = page
        
        # --- UI ELEMENTS ---
        
        # Stato
        self.progress_ring = ft.ProgressRing(width=16, height=16, stroke_width=2, visible=False)
        self.status_text = ft.Text("Pronto per l'elaborazione", color=ft.Colors.WHITE70)
        
        # --- CONFIGURAZIONE BASE ---
        self.switch_instant = ft.Switch(
            label="Usa Euristiche (Soluzione Istantanea)", 
            value=True,
            on_change=self._on_method_change
        )
        self.slider_max_time = ft.Slider(min=10, max=1800, divisions=179, label="Tempo Max: {value}s", value=300)
        self.slider_top_k = ft.Slider(min=1, max=10, divisions=9, label="Mostra {value} soluzioni", value=5)
        
        # --- OPZIONI AVANZATE ---
        self.advanced_container = ft.Column(visible=True, spacing=10)
        self.advanced_options = ft.Column(visible=False, spacing=15)
        
        # Pesi (0-5)
        self.weight_time = ft.Slider(min=0, max=5, divisions=10, label="Tempo: {value}", value=1.0)
        self.weight_resource = ft.Slider(min=0, max=5, divisions=10, label="Risorse: {value}", value=1.0)
        self.weight_priority = ft.Slider(min=0, max=5, divisions=10, label="Priorità: {value}", value=1.0)
        self.weight_tardiness = ft.Slider(min=0, max=5, divisions=10, label="Ritardo: {value}", value=1.0)
        
        # Regola di Priorità
        self.dropdown_rule = ft.Dropdown(
            label="Regola di Priorità",
            options=[
                ft.dropdown.Option("spt", "Shortest Process Time (SPT)"),
                ft.dropdown.Option("mts", "Most Total Successors (MTS)"),
                ft.dropdown.Option("grd", "Greatest Resource Demand (GRD)"),
                ft.dropdown.Option("lft_rcpsp", "Latest Finishing Time (LFT)"),
                ft.dropdown.Option("lst_rcpsp", "Latest Starting Time (LST)"),
                ft.dropdown.Option("mslk_rcpsp", "Minimum Slack Time (MSLK)"),
            ],
            value=None,
            hint_text="Auto"
        )
        
        # Overlay per bloccare SOLO la colonna parametri
        self.params_overlay = ft.Container(
            expand=True,
            bgcolor=ft.Colors.with_opacity(0.01, ft.Colors.BLACK), # Quasi invisibile ma intercetta i click
            visible=False,
            border_radius=16,
            on_click=lambda _: None # Cattura e ignora il click
        )

        
        # Pulsanti Esecuzione (Fuori dall'overlay)
        self.btn_run = ft.ElevatedButton(
            "Avvia Schedulazione",
            icon=ft.Icons.PLAY_ARROW_ROUNDED,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_ACCENT_700,
                padding=20,
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            on_click=lambda e: self.controller.start_scheduling(e)
        )
        
        self.btn_stop = ft.ElevatedButton(
            "Interrompi",
            icon=ft.Icons.STOP_ROUNDED,
            visible=False,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.RED_ACCENT_700,
                padding=20,
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            on_click=lambda e: self.controller.stop_scheduling(e)
        )

        # Sezione Risultati
        self.results_container = ft.Container(visible=False)

    def build_view(self):
        # Setup Avanzate
        self.advanced_options.controls = [
            ft.Text("Configurazione Avanzata (solo Euristiche)", size=16, weight=ft.FontWeight.W_500, color=ft.Colors.BLUE_ACCENT_400),
            ft.Divider(height=1, color=ft.Colors.WHITE10),
            ft.Text("Pesi Funzione Obiettivo (0-5)", size=14, color=ft.Colors.WHITE70),
            ft.Row([
                ft.Column([ft.Text("Tempo", size=12), self.weight_time], expand=1),
                ft.Column([ft.Text("Risorse", size=12), self.weight_resource], expand=1),
            ]),
            ft.Row([
                ft.Column([ft.Text("Priorità", size=12), self.weight_priority], expand=1),
                ft.Column([ft.Text("Ritardo", size=12), self.weight_tardiness], expand=1),
            ]),
            self.dropdown_rule,
        ]

        self.btn_advanced_toggle = ft.TextButton(
            "Opzioni Avanzate", 
            icon=ft.Icons.SETTINGS,
            on_click=self._toggle_advanced
        )

        self.advanced_container.controls = [
            self.btn_advanced_toggle,
            self.advanced_options
        ]

        # Colonna Parametri (Protetta da Stack + Overlay)
        col_params = ft.Stack([
            ft.Container(
                padding=25,
                bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.WHITE),
                border_radius=16,
                content=ft.Column([
                    ft.Text("Parametri Base", size=18, weight=ft.FontWeight.W_500),
                    self.switch_instant,
                    ft.Text("Limite Tempo Esecuzione (Secondi)", size=14, color=ft.Colors.WHITE70),
                    self.slider_max_time,
                    ft.Text("Numero massimo di soluzioni alternative", size=14, color=ft.Colors.WHITE70),
                    self.slider_top_k,
                    ft.Container(height=10),
                    self.advanced_container
                ])
            ),
            self.params_overlay
        ], expand=2)

        # Colonna Esecuzione (Sempre interattiva)
        col_exec = ft.Container(
            expand=1,
            padding=25,
            bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.BLUE_ACCENT_700),
            border_radius=16,
            content=ft.Column([
                ft.Text("Esecuzione", size=18, weight=ft.FontWeight.W_500),
                ft.Divider(height=1, color=ft.Colors.WHITE10),
                ft.Row([self.progress_ring, self.status_text], spacing=10),
                ft.Container(height=20),
                self.btn_run,
                self.btn_stop,
                ft.Text(
                    "Puoi interrompere il calcolo in ogni momento se impiega troppo.",
                    size=12, color=ft.Colors.WHITE38, italic=True
                )
            ])
        )

        self.controls = [
            ft.Container(
                padding=30,
                expand=True,
                content=ft.Column(
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                    spacing=20,
                    controls=[
                        # Header
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Column([
                                    ft.Text("Configurazione Schedulazione", size=32, weight=ft.FontWeight.BOLD),
                                    ft.Text(f"Progetto: {self.project.name}", color=ft.Colors.BLUE_ACCENT_400, size=16),
                                ]),
                                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: self.controller.go_back(e))
                            ]
                        ),
                        ft.Divider(height=1, color=ft.Colors.WHITE24),
                        # Corpo
                        ft.Row(
                            vertical_alignment=ft.CrossAxisAlignment.START,
                            controls=[col_params, col_exec]
                        ),
                        # Risultati
                        self.results_container
                    ]
                )
            )
        ]

    def _toggle_advanced(self, e):
        self.advanced_options.visible = not self.advanced_options.visible
        e.control.icon = ft.Icons.KEYBOARD_ARROW_UP if self.advanced_options.visible else ft.Icons.SETTINGS
        self.update()

    def _on_method_change(self, e):
        self.advanced_container.visible = self.switch_instant.value
        self.update()

    def get_params(self):
        return {
            "instant_sol": self.switch_instant.value,
            "max_time": int(self.slider_max_time.value),
            "top_k": int(self.slider_top_k.value),
            "time_weight": float(self.weight_time.value),
            "resource_weight": float(self.weight_resource.value),
            "priority_weight": float(self.weight_priority.value),
            "tardiness_weight": float(self.weight_tardiness.value),
            "priority_rule": self.dropdown_rule.value if self.switch_instant.value else None
        }

    def show_loading(self, loading: bool):
        self.progress_ring.visible = loading
        self.btn_run.visible = not loading
        self.btn_stop.visible = loading
        self.params_overlay.visible = loading # Blocca solo i parametri
        self.status_text.value = "Calcolo in corso..." if loading else "Pronto."
        self.status_text.color = ft.Colors.BLUE_ACCENT_200 if loading else ft.Colors.WHITE70
        self.update()

    def show_results(self, summary):
        self.results_container.visible = True
        self.results_container.content = ft.Container(
            padding=25,
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.GREEN_400),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.2, ft.Colors.GREEN_400)),
            border_radius=16,
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_400, size=28),
                    ft.Text("Schedulazione Completata", size=20, weight=ft.FontWeight.BOLD),
                ]),
                ft.Row([
                    self._stat_item("Makespan", str(summary["best_makespan"]), ft.Icons.TIMER),
                    self._stat_item("Score", f"{summary['best_score']:.2f}" if summary['best_score'] else "-", ft.Icons.STAR_HALF),
                    self._stat_item("Soluzioni", str(summary["num_solutions"]), ft.Icons.LIST_ALT),
                    self._stat_item("Difficoltà", summary["difficulty"].upper(), ft.Icons.SPEED),
                ]),
                ft.Divider(height=1, color=ft.Colors.WHITE10),
                ft.Row([
                    ft.Text(f"Metodo: {summary['method'].value}", size=14, color=ft.Colors.WHITE70),
                    ft.VerticalDivider(),
                    ft.Text(f"Ora: {summary['created_at']}", size=14, color=ft.Colors.WHITE70),
                ]),
                ft.ElevatedButton(
                    "Visualizza Diagramma di Gantt", 
                    icon=ft.Icons.AUTO_GRAPH,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE),
                    on_click=lambda _: self.page.go(f"/gantt?project_id={self.project.id}")
                )
            ])
        )
        self.update()

    def _stat_item(self, label, value, icon):
        return ft.Container(
            expand=1,
            content=ft.Column([
                ft.Row([ft.Icon(icon, size=16, color=ft.Colors.BLUE_ACCENT_200), ft.Text(label, size=12, color=ft.Colors.WHITE70)]),
                ft.Text(value, size=22, weight=ft.FontWeight.BOLD),
            ], spacing=5)
        )

    def show_error(self, message):
        self.status_text.value = f"Errore: {message}"
        self.status_text.color = ft.Colors.RED_ACCENT_400
        self.update()
