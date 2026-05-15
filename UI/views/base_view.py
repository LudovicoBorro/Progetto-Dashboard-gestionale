import flet as ft
from UI.widgets.sidebar import Sidebar

class BaseView(ft.View):
    """
    Classe base per tutte le View dell'applicazione che condividono lo stesso layout 
    (Sidebar + Content).
    """
    def __init__(self, route: str, controller=None):
        super().__init__(route=route)
        self._controller = controller
        self._page_ref = None # Verrà popolato da app.py se necessario

    def set_content(self, controls: list[ft.Control], scroll=ft.ScrollMode.AUTO):
        """
        Metodo helper per impostare il contenuto principale mantenendo la Sidebar.
        """
        main_content = ft.Container(
            expand=True,
            padding=20,
            content=ft.Column(
                scroll=scroll,
                spacing=20,
                controls=controls
            )
        )

        layout = ft.Row(
            expand=True,
            controls=[
                Sidebar(self.controller),
                ft.VerticalDivider(width=1),
                main_content
            ]
        )

        self.controls = [layout]

    @property
    def controller(self):
        return self._controller

    @controller.setter
    def controller(self, controller):
        self._controller = controller
        # Quando il controller viene impostato, di solito vogliamo triggerare il build
        if hasattr(self, "build_view"):
            self.build_view()

    def update(self):
        page = self.page or self._page_ref
        if not page:
            return

        try:
            page.update()
        except Exception:
            # Fallback utile quando update viene richiesto da thread worker
            if hasattr(page, "schedule_update"):
                page.schedule_update()
            else:
                raise
