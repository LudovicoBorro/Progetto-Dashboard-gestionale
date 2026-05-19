from UI.controllers.base_controller import BaseController
from UI.services.gantt_service import GanttService
import pandas as pd

class GanttController(BaseController):
    """
    Controller per la vista Gantt.
    Gestisce il recupero dati dal database tramite GanttService e la navigazione.
    """
    def __init__(self, view, project):
        super().__init__(view)
        self.project = project

    def get_dataframe(self) -> pd.DataFrame:
        """
        Recupera il DataFrame delle attività schedulate per il progetto corrente.
        Se si verifica un errore o non ci sono dati, restituisce None.
        """
        try:
            _, df = GanttService.get_gantt_dataframe(self.project.id)
            return df
        except Exception as e:
            print(f"Errore durante il recupero dei dati per il Gantt: {e}")
            return None

    def go_back(self, e):
        """Ritorna alla vista di dettaglio del progetto."""
        self.view.page.go(f"/project_details?id={self.project.id}")
