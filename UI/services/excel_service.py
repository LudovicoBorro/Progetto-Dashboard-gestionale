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
            from data.models.project_resource import ProjectResource
            from data.repositories.project_resource_repository import ProjectResourceRepository
            from sqlmodel import delete
            
            # 1. Pulizia attività esistenti per questo progetto
            statement = delete(Activity).where(Activity.project_id == self.project.id)
            session.exec(statement)
            
            # 1.1 Pulizia risorse associate al progetto
            statement_res = delete(ProjectResource).where(ProjectResource.project_id == self.project.id)
            session.exec(statement_res)

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
            
            # 2.1 Gestione delle Risorse del Progetto
            proj_res_repo = ProjectResourceRepository(session)
            default_colors = ["#FF5733", "#33FF57", "#3357FF", "#F3FF33", "#FF33A8", 
                                "#33FFF3", "#FFA833", "#FF9933", "#99FF33", "#A833FF", "#33A8FF",
                                "#33FF99", "#FF3333"]
            
            if in_data.resource_names and in_data.resources:
                for i, res_name in enumerate(in_data.resource_names):
                    res_capacity = in_data.resources[i]
                    if isinstance(res_capacity, tuple):
                        cap_min, cap_max = res_capacity
                    else:
                        cap_min = res_capacity
                        cap_max = None
                        
                    color_hex = default_colors[i % len(default_colors)]
                    
                    proj_res = ProjectResource(
                        project_id=self.project.id,
                        name=res_name,
                        capacity_min=cap_min,
                        capacity_max=cap_max,
                        color_hex=color_hex
                    )
                    session.add(proj_res)

            # 3. Aggiorna il progetto tramite repository
            repo = ProjectRepository(session)
            repo.update(self.project)
