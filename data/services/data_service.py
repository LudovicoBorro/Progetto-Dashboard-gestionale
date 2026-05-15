import uuid
from typing import Union, Dict, List, Any
from sqlmodel import Session
from ..models import Experiment, Schedule, ScheduleActivity, Activity, ProblemType, Method
from ..repositories.experiment_repository import ExperimentRepository
from ..repositories.schedule_repository import ScheduleRepository
from ..repositories.schedule_activity_repository import ScheduleActivityRepository
from ..repositories.activity_repository import ActivityRepository

class DataService:
    def __init__(self, session: Session):
        self.session = session
        self.experiment_repo = ExperimentRepository(session)
        self.schedule_repo = ScheduleRepository(session)
        self.sa_repo = ScheduleActivityRepository(session)
        self.activity_repo = ActivityRepository(session)

    def save_solver_result(self, project_id: uuid.UUID, solver_output: Any) -> Experiment:
        """
        Mappa e salva i risultati dell'orchestrator nel database usando il nuovo SolutionDTO.
        """
        from solver.dataclasses.soluzione_orchestrator import SolutionDTO, SingleSolution

        # 1. Normalizzazione Input
        if not isinstance(solver_output, SolutionDTO):
            # Se arriva un dict (legacy), Pydantic lo convalida
            solution_dto = SolutionDTO(**solver_output) if isinstance(solver_output, dict) else solver_output
        else:
            solution_dto = solver_output

        # 2. Estrazione Metadati Globali
        orchestrator_data = solution_dto.model_dump(by_alias=True)
        results_meta = solution_dto.results or {}
        
        # Cerchiamo la configurazione migliore (fondamentale per B&B)
        # Se siamo in B&B, la config è dentro additional_info["best_config"]
        best_config = solution_dto.additional_info.get("best_config") or results_meta.get("config", {})

        # 3. Creazione Experiment
        experiment = Experiment(
            project_id=project_id,
            problem_type=ProblemType(solution_dto.problem_type),
            method=Method(solution_dto.solution_type),
            search_strategy=solution_dto.search_strategy,
            num_runs=results_meta.get("n_runs", 1) if isinstance(results_meta, dict) else 1,

            experiment_config_json={
                "difficulty": solution_dto.problem_difficulty,
                "search_strategy": solution_dto.search_strategy,
                "global_solver_results": results_meta,
                "additional_info": solution_dto.additional_info
            }
        )
        self.experiment_repo.create(experiment)

        # 4. Mappatura Activity ID
        activities = self.activity_repo.get_by_project(project_id)
        activity_map: Dict[int, Activity] = {a.id_for_project: a for a in activities}

        # 5. Elaborazione delle Top-K soluzioni
        ranking = solution_dto.ranking
        seen_signatures = set()
        unique_solutions: List[SingleSolution] = []

        def add_unique(sol: SingleSolution):
            if not sol: return
            # La firma è lo schedule dict (start times)
            sig = str(sol.schedule_dict)
            if sig not in seen_signatures:
                seen_signatures.add(sig)
                unique_solutions.append(sol)

        add_unique(ranking.best_solution)
        for sol in ranking.top_k_makespan: add_unique(sol)
        for sol in ranking.top_k_score: add_unique(sol)

        # 6. Salvataggio degli Schedule
        for sol in unique_solutions:
            # Una soluzione può avere la sua config (nel caso del B&B che esplora scenari diversi)
            sol_config = getattr(sol, "rank_info", {}).get("config") if sol.rank_info else None
            sol_config = sol_config or best_config

            new_schedule = Schedule(
                experiment_id=experiment.id,
                makespan=sol.makespan,
                score=sol.score,
                config_json={
                    "regola_usata": sol.regola,
                    "penalità_totale": sol.penalty,
                    "parametri_run": sol_config,
                    "elapsed_time": sol.elapsed_time,
                    "solver_metadata": sol.rank_info
                }
            )
            self.schedule_repo.create(new_schedule)

            # 7. Salvataggio ScheduleActivity
            # Usiamo sol.soluzione (lista di dict) che è il formato standard per il salvataggio
            if sol.soluzione:
                for item in sol.soluzione:
                    act_id = item.get("activity")
                    if act_id in activity_map:
                        activity = activity_map[act_id]
                        
                        # Recupero vincoli temporali dalla config se presenti (per visualizzazione Gantt)
                        release_date = None
                        deadline = None
                        if sol_config:
                            rd_list = sol_config.get("release_dates")
                            dd_list = sol_config.get("due_dates")
                            if rd_list and act_id < len(rd_list): release_date = rd_list[act_id]
                            if dd_list and act_id < len(dd_list): deadline = dd_list[act_id]

                        sa = ScheduleActivity(
                            schedule_id=new_schedule.id,
                            activity_id=activity.id,
                            start_time=item.get("start"),
                            end_time=item.get("end"),
                            duration=item.get("end") - item.get("start"),
                            resource_usage=activity.activity_config_json.get("resource_requirements", {}),
                            release_date=release_date,
                            deadline=deadline
                        )
                        self.sa_repo.create(sa)

        return experiment
