import uuid
import threading
from typing import Dict, Any, Optional, Callable
from solver.orchestrator import SolverOrchestrator
from UI.services.project_service import ProjectService
from data.services.data_service import DataService
from data.database import get_session
from data.models import Experiment

class SchedulingService:
    def __init__(self):
        self._orchestrator = SolverOrchestrator()

    def run_scheduling(
        self, 
        project_id: uuid.UUID, 
        params: Dict[str, Any],
        on_success: Optional[Callable[[Experiment], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        thread_runner: Optional[Callable[[Callable[[], None]], None]] = None
    ):
        """
        Esegue la schedulazione in un thread separato per non bloccare la UI.
        """
        def task():
            try:
                # 1. Recupero dati input
                input_data = ProjectService.get_input_data(project_id)
                
                # 2. Aggiornamento parametri input con quelli scelti dall'utente nella view
                # Ad esempio: instant_sol, rcpsp_max, ecc.
                for key, value in params.items():
                    if hasattr(input_data, key):
                        setattr(input_data, key, value)
                
                # 3. Esecuzione Solver
                solver_result = self._orchestrator.choose_model(input_data=input_data, **params)
                
                # 4. Salvataggio risultati nel DB
                with get_session() as session:
                    data_service = DataService(session)
                    experiment = data_service.save_solver_result(project_id, solver_result)
                    session.commit()
                    
                    # Ricarichiamo l'esperimento con le relazioni per il sommario
                    session.refresh(experiment)
                    # Forziamo il caricamento dei schedules (essenziale per il sommario fuori dalla sessione)
                    _ = experiment.schedules 
                
                # 5. Callback di successo
                if on_success:
                    on_success(experiment)

                    
            except Exception as e:
                import traceback
                traceback.print_exc()
                if on_error:
                    on_error(str(e))

        # Lancio il thread
        if thread_runner:
            thread_runner(task)
        else:
            thread = threading.Thread(target=task, daemon=True, name="SchedulingWorker")
            thread.start()

    @staticmethod
    def get_summary(experiment: Experiment) -> Dict[str, Any]:
        """
        Restituisce un riepilogo leggibile dell'esperimento concluso.
        """
        best_schedule = None
        if experiment.schedules:
            # Prendiamo lo schedule con il makespan minore (o lo score migliore se RCPSP_MAX)
            if experiment.problem_type == "RCPSP_MAX":
                best_schedule = min(experiment.schedules, key=lambda s: s.score if s.score is not None else float('inf'))
            else:
                best_schedule = min(experiment.schedules, key=lambda s: s.makespan if s.makespan is not None else float('inf'))

        return {
            "method": experiment.method,
            "difficulty": experiment.experiment_config_json.get("difficulty"),
            "num_solutions": len(experiment.schedules),
            "best_makespan": best_schedule.makespan if best_schedule else None,
            "best_score": best_schedule.score if best_schedule else None,
            "created_at": experiment.created_at.strftime("%H:%M:%S")
        }
