from ctypes import alignment
import flet as ft
from flet_charts import MatplotlibChart
import matplotlib
import matplotlib.text
from UI.views.base_view import BaseView
from UI.widgets.gantt_chart import GanttChart

class GanttView(BaseView):
    """
    Vista dedicata alla visualizzazione del Diagramma di Gantt di un progetto.
    Integra il grafico matplotlib all'interno dell'interfaccia Flet con uno stile dark coerente.
    """
    def __init__(self, page: ft.Page, project):
        super().__init__(route="/gantt", controller=None)
        self.project = project
        self._page_ref = page

    def build_view(self):
        # Header con pulsante Indietro e titolo
        header = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Column([
                    ft.Text("Diagramma di Gantt", size=32, weight=ft.FontWeight.BOLD),
                    ft.Text(f"Progetto: {self.project.name}", color=ft.Colors.BLUE_ACCENT_400, size=16),
                ]),
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    icon_color=ft.Colors.WHITE,
                    on_click=self.controller.go_back
                )
            ]
        )

        # Recupera il dataframe dal controller
        df = self.controller.get_dataframe()

        if df is None or df.empty:
            chart_content = ft.Container(
                content=ft.Text(
                    "Nessun dato di schedulazione disponibile per questo progetto.",
                    size=16,
                    color=ft.Colors.WHITE70
                ),
                alignment=ft.MainAxisAlignment.CENTER,
                padding=50
            )
        else:
            # Crea e configura il grafico
            gantt = GanttChart(df, self.project)
            fig, ax = gantt.plot()

            # Configurazione estetica per adattare Matplotlib al tema Dark di Flet
            bg_color = "#ffffff"
            chart_bg = "#ffffff"
            border_color = "#d1d5db"
            text_color = "#111827"
            muted_text = "#4b5563"
            grid_color = "#cbd5e1"

            fig.patch.set_facecolor(bg_color)
            ax.set_facecolor(chart_bg)

            # Titolo ed etichette assi
            ax.title.set_color(text_color)
            if ax.xaxis.label:
                ax.xaxis.label.set_color(muted_text)
            if ax.yaxis.label:
                ax.yaxis.label.set_color(muted_text)

            # Colore dei bordi (spines)
            for spine in ax.spines.values():
                spine.set_color(border_color)

            # Colore dei ticks e delle etichette (nomi attività, date)
            ax.tick_params(colors=muted_text, which='both')

            # Griglia di background
            ax.xaxis.grid(True, color=grid_color, alpha=0.9, linestyle="--", linewidth=0.9)

            # Legenda delle durate
            legend = ax.get_legend()
            if legend:
                legend.get_frame().set_facecolor(chart_bg)
                legend.get_frame().set_edgecolor(border_color)
                for text in legend.get_texts():
                    text.set_color(text_color)
                if legend.get_title():
                    legend.get_title().set_color(text_color)

            # Ricolora il testo della linea verticale di "Oggi" in rosso/rosa per risaltare
            for child in ax.get_children():
                if isinstance(child, matplotlib.text.Text) and child.get_text() != ax.title.get_text():
                    # Se non è il titolo principale, è l'indicatore temporale
                    child.set_color("#f43f5e")

            # Inserisce il grafico matplotlib nel container Flet
            chart_content = ft.Container(
                bgcolor=bg_color,
                border_radius=16,
                border=ft.Border.all(1, border_color),
                padding=20,
                height=700,
                content=MatplotlibChart(figure=fig, expand=True),
                expand=True,
            )

        # Sezione delle schede statistiche in alto
        stats_row = ft.Row(
            spacing=20,
            controls=[
                self._stat_card("Attività Totali", str(len(df)) if df is not None else "0", ft.Icons.LIST_ALT),
                self._stat_card("Data Inizio", self.project.start_date.strftime("%d/%m/%Y"), ft.Icons.DATE_RANGE),
                self._stat_card("Data Fine Prevista", self.project.end_date.strftime("%d/%m/%Y"), ft.Icons.FLAG),
                self._stat_card("Stato", str(self.project.status.value), ft.Icons.INFO_OUTLINE),
            ]
        )

        # Imposta la struttura della pagina
        self.set_content(
            controls=[
                header,
                ft.Divider(height=1, color=ft.Colors.WHITE24),
                stats_row,
                chart_content
            ]
        )

    def _stat_card(self, title: str, value: str, icon: str):
        return ft.Container(
            expand=1,
            bgcolor="#1e293b",
            border_radius=12,
            border=ft.Border.all(1, "#334155"),
            padding=15,
            content=ft.Column([
                ft.Row([
                    ft.Icon(icon, color=ft.Colors.BLUE_ACCENT_200, size=20),
                    ft.Text(title, size=14, color=ft.Colors.WHITE70, weight=ft.FontWeight.W_500)
                ], spacing=10),
                ft.Text(value, size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
            ], spacing=5)
        )
