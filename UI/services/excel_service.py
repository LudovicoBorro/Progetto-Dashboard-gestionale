from datetime import datetime
from data.repositories.project_repository import ProjectRepository
from data.database import get_session
from solver.dataclasses.input_data import InputData
from data.services.excel_import_service import ExcelImportService
from data.models import Project

class ExcelService:
    def __init__(self):
        self.project = None
        self.file_path = None
        self.input_data = None

    def get_instance_data_from_excel(self, file_path: str, project: Project) -> InputData:
        if file_path is None:
            raise ValueError("Il file Excel non è stato fornito.")
        if project is None:
            raise ValueError("Il progetto non è stato fornito.")
        self.project = project
        self.file_path = file_path

        self._import_instance_from_excel()
        self._save_into_db()

    def _import_instance_from_excel(self):
        excel_import_service = ExcelImportService(file_path=self.file_path)
        self.input_data = excel_import_service.load_instance_from_excel(start_date_project=self.project.start_date, end_date_project=self.project.end_date)
        
    def _save_into_db(self):
        """
        Funzione per salvare l'istanza importata da Excel dentro il database,
        in modo tale da salvare subito i dati, prima di avviare il solver.
        """
        in_data = self.input_data
        
        # Aggiorna il progetto
        self.project.num_activities = in_data.n
        self.project.horizon_days = in_data.horizon
        self.project.input_data_json = in_data.model_dump()
        self.project.last_edited_at = datetime.now()
        self.project.project_config_json = {
            "rcpsp_max": in_data.rcpsp_max,
            "has_intervals": in_data.has_intervals,
        }

        with get_session() as session:
            from data.models.activity import Activity
            from sqlmodel import delete
            
            # 1. Pulizia attività esistenti per questo progetto
            statement = delete(Activity).where(Activity.project_id == self.project.id)
            session.exec(statement)
            
            # 2. Creazione nuove attività
            new_activities = []
            for i in range(in_data.n):
                name = in_data.activity_names[i] if in_data.activity_names else f"Attività {i+1}"
                duration = in_data.durations[i]
                
                activity = Activity(
                    project_id=self.project.id,
                    id_for_project=i+1,
                    name=name,
                    is_dummy=False,
                    activity_config_json={
                        "duration": duration,
                        "release_date": in_data.release_dates[i] if in_data.release_dates else None,
                        "due_date": in_data.due_dates[i] if in_data.due_dates else None,
                        "consumption": in_data.consumption[i] if in_data.consumption else []
                    }
                )
                new_activities.append(activity)
            
            session.add_all(new_activities)
            
            # 3. Aggiorna il progetto tramite repository
            repo = ProjectRepository(session)
            repo.update(self.project)
