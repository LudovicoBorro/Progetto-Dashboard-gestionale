import asyncio
from UI.widgets.error_alert import ErrorAlert
from UI.controllers.base_controller import BaseController
from data.models.project import Project
import flet as ft
import os
import time
from UI.services.excel_service import ExcelService
from UI.services.project_service import ProjectService

class ProjectController(BaseController):

    def __init__(self, view, project: Project):
        super().__init__(view)
        self.project = project
        self._last_mtime = None
        self._monitoring = False

    # ------------------------------------------------------------------ #
    #  Scheduling
    # ------------------------------------------------------------------ #

    def go_scheduling_view(self, e):
        """
        Reindirizza alla pagina per eseguire le schedulazioni 
        del progetto.
        """
        self.view.page.go(f"/scheduling?id={self.project.id}")
        print(f"Chiamata la schedulazione per il progetto: {self.project.name}")

    def get_activities(self) -> list:
        """Recupera le attività del progetto tramite il service."""
        from UI.services.project_service import ProjectService
        return ProjectService.get_activities_by_project(self.project.id)

    # ------------------------------------------------------------------ #
    #  Excel: apertura e monitoraggio
    # ------------------------------------------------------------------ #

    def open_excel_file(self, e):
        """Apre il file Excel."""
        file_path = os.path.abspath("data/files/input_data.xlsx")
        page = self.view.page or self.view._page_ref

        if not os.path.exists(file_path):
            self._show_snackbar(f"Errore: File non trovato in {file_path}")
            return

        # Salviamo il timestamp prima di aprire
        self._last_mtime = os.path.getmtime(file_path)

        # Apriamo il file
        os.startfile(file_path)

        # Avviamo il monitoraggio
        if not self._monitoring:
            self._monitoring = True
            import threading
            threading.Thread(target=self._watch_excel_file, daemon=True).start()

    def create_info_dialog(self, e):
        # Mostriamo il dialogo informativo
        page = self.view.page or self.view._page_ref
        if page:
            if hasattr(page, 'open'):
                page.open(self.view.info_edit_dialog)
            else:
                self.view.info_edit_dialog.open = True
                if self.view.info_edit_dialog not in page.overlay:
                    page.overlay.append(self.view.info_edit_dialog)
                page.update()

    def _watch_excel_file(self):
        """Controlla ogni secondo se il file Excel è stato salvato."""
        file_path = os.path.abspath("data/files/input_data.xlsx")
        while self._monitoring:
            if os.path.exists(file_path):
                current_mtime = os.path.getmtime(file_path)
                if self._last_mtime and current_mtime > self._last_mtime:
                    # File modificato: sblocchiamo il pulsante
                    self.view.btn_import.disabled = False
                    self.view.update()
                    self._show_snackbar("File salvato! Ora puoi cliccare su 'Importa Dati'.")
                    self._monitoring = False
                    break
            time.sleep(1)

    # ------------------------------------------------------------------ #
    #  Import dati
    # ------------------------------------------------------------------ #

    def confirm_import(self, e):
        """Mostra il dialogo di conferma prima dell'importazione."""
        page = self.view.page or self.view._page_ref
        if page:
            if hasattr(page, 'open'):
                page.open(self.view.confirm_dialog)
            else:
                self.view.confirm_dialog.open = True
                if self.view.confirm_dialog not in page.overlay:
                    page.overlay.append(self.view.confirm_dialog)
                page.update()
            print(f"DEBUG: Dialogo di conferma aperto per '{self.view.project.name}'")

    def import_project_data(self, e):
        """Esegue l'importazione dei dati dal file Excel nel DB."""
        print("DEBUG: Entrato in import_project_data")

        page = self.view.page or self.view._page_ref

        # Chiudiamo il dialogo di conferma
        if page:
            if hasattr(page, 'close'):
                page.close(self.view.confirm_dialog)
            else:
                self.view.confirm_dialog.open = False
                page.update()
                
        async def _do_import():
            try:
                await asyncio.sleep(0.2) # Breve ritardo per animazione
                
                excel_service = ExcelService()
                excel_service.get_instance_data_from_excel("data/files/input_data.xlsx", self.project)

                # Ricarichiamo il progetto aggiornato dal DB
                updated_project = ProjectService.get_project_by_id(self.project.id)
                self.project = updated_project
                self.view.project = updated_project

                # Reset del pulsante e ricostruzione vista
                self.view.btn_import.disabled = True
                self.view.build_view()
                self.view.update()
                self._show_snackbar("Importazione completata con successo!")
                print("Importazione completata con successo!")

            except Exception as ex:
                print(f"Errore durante l'importazione: {ex}")
                import traceback
                traceback.print_exc()
                def close_err(e):
                    self.error_alert.open = False
                    if self.view.page or self.view._page_ref:
                        p = self.view.page or self.view._page_ref
                        if hasattr(p, 'close'):
                            p.close(self.error_alert)
                        else:
                            p.update()

                self.error_alert = ErrorAlert(
                    error_message=f"Errore durante l'importazione: {ex}",
                    title="Errore",
                    actions=[
                        ft.TextButton("OK", on_click=close_err)
                    ],
                )
                
                p2 = self.view.page or self.view._page_ref
                if p2:
                    if hasattr(p2, 'open'):
                        p2.open(self.error_alert)
                    else:
                        self.error_alert.open = True
                        if self.error_alert not in p2.overlay:
                            p2.overlay.append(self.error_alert)
                    
                    # Forza l'aggiornamento della UI dal thread in background
                    p2.update()

        page.run_task(_do_import)

    # ------------------------------------------------------------------ #
    #  Helper UI
    # ------------------------------------------------------------------ #

    def _show_snackbar(self, message: str):
        page = self.view.page or self.view._page_ref
        if page:
            page.snack_bar = ft.SnackBar(ft.Text(message))
            page.snack_bar.open = True
            page.update()
        else:
            print(f"[Snackbar] {message}")
