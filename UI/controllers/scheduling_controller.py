from UI.controllers.base_controller import BaseController
from data.models.project import Project
from UI.services.scheduling_service import SchedulingService
import flet as ft

class SchedulingController(BaseController):

    def __init__(self, view, project: Project):
        super().__init__(view)
        self.project = project
        self.scheduling_service = SchedulingService()
        self.is_running = False
        self._is_cancelled = False

    def start_scheduling(self, e):
        """Avvia il processo di schedulazione."""
        if self.is_running:
            return

        # 1. Recupero parametri dalla view
        params = self.view.get_params()
        
        # 2. Reset flag cancellazione e aggiornamento UI
        self._is_cancelled = False
        self.is_running = True
        self.view.show_loading(True)
        self.view.update()

        # 3. Chiamata al service
        self.scheduling_service.run_scheduling(
            project_id=self.project.id,
            params=params,
            on_success=lambda experiment: self._dispatch_to_ui(self._on_scheduling_success, experiment),
            on_error=lambda error_message: self._dispatch_to_ui(self._on_scheduling_error, error_message)
        )


    def _dispatch_to_ui(self, callback, *args):
        """Esegue callback sul thread UI quando disponibile."""
        page = self.view.page or getattr(self.view, "_page_ref", None)
        if page and hasattr(page, "call_from_thread"):
            page.call_from_thread(callback, *args)
        else:
            callback(*args)

    def stop_scheduling(self, e):
        """Interrompe visivamente la schedulazione (sgancio)."""
        if not self.is_running:
            return
            
        self._is_cancelled = True
        self.is_running = False
        
        # Ripristiniamo la UI subito
        self.view.show_loading(False)
        self.view.show_error("Schedulazione interrotta dall'utente.")
        self.view.update()

    def _on_scheduling_success(self, experiment):
        """Callback eseguita al termine con successo."""
        if self._is_cancelled:
            return # Ignoriamo il risultato se l'utente ha interrotto
            
        self.is_running = False
        summary = self.scheduling_service.get_summary(experiment)

        print("[DEBUG]: Stampa in corso della soluzione letta dal DB...")
        print(f"[DEBUG]: {summary}")
        
        # Aggiorniamo la UI
        self.view.show_loading(False)
        self.view.show_results(summary)
        self.view.update()

    def _on_scheduling_error(self, error_message):
        """Callback eseguita in caso di errore."""
        if self._is_cancelled:
            return
        
        print("[DEBUG]: Errore nel salvataggio o nella lettura del DB...")
            
        self.is_running = False
        self.view.show_loading(False)
        self.view.show_error(error_message)
        self.view.update()

    def go_back(self, e):
        """Torna alla pagina dei dettagli del progetto."""
        self.view.page.go(f"/project_details?id={self.project.id}")