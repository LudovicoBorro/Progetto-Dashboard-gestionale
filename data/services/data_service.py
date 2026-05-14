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
        Mappa e salva i risultati dell'orchestrator nel database con supporto completo a RCPSP/MAX e B&B.
        """
        # 1. Identificazione tipo di output e configurazione globale
        is_bb = hasattr(solver_output, 'config') and hasattr(solver_output, 'solution')
        
        if is_bb:
            orchestrator_data = solver_output.solution.model_dump()
            global_config = solver_output.config.model_dump()
            results_meta = orchestrator_data.get("results") or {}
        else:
            orchestrator_data = solver_output if isinstance(solver_output, dict) else solver_output.model_dump()
            results_meta = orchestrator_data.get("results") or {}
            global_config = results_meta.get("config", {})



        # 2. Creazione Experiment
        # Leggiamo il tipo di problema dal flag esplicito dell'orchestrator
        is_rcpsp_max = orchestrator_data.get("is_rcpsp_max", False)
        problem_type_str = "RCPSP_MAX" if is_rcpsp_max else "RCPSP"
        
        experiment = Experiment(
            project_id=project_id,
            problem_type=ProblemType(problem_type_str),

            method=Method(orchestrator_data.get("type", "heuristic_fallback")),
            num_runs=results_meta.get("n_runs", 1),

            experiment_config_json={
                "difficulty": orchestrator_data.get("problem_difficulty"),
                "is_branch_and_bound": is_bb,
                "global_solver_results": orchestrator_data.get("results")
            }
        )
        self.experiment_repo.create(experiment)

        # 3. Mappatura Activity ID
        activities = self.activity_repo.get_by_project(project_id)
        activity_map: Dict[int, Activity] = {a.id_for_project: a for a in activities}

        # 4. Elaborazione delle Top-K soluzioni
        best_data = orchestrator_data.get("best", {})
        seen_schedules = set()
        all_top_solutions = []
        
        # Consideriamo sia le migliori per makespan che per score
        sources = [best_data.get("top_k_makespan", []), best_data.get("top_k_score", [])]
        if best_data.get("best"):
            sources.append([best_data.get("best")])

        for source in sources:
            for sol in source:
                # La firma della soluzione è lo schedule (id -> start_time)
                sol_signature = str(sol.get("soluzione") or sol.get("schedule"))
                if sol_signature not in seen_schedules:
                    seen_schedules.add(sol_signature)
                    all_top_solutions.append(sol)

        # 5. Salvataggio degli Schedule
        for sol in all_top_solutions:
            # Una soluzione può avere una configurazione specifica (specialmente in B&B)
            # Se non presente, usiamo la global_config dell'esperimento
            sol_config = sol.get("config") or global_config

            new_schedule = Schedule(
                experiment_id=experiment.id,
                makespan=sol.get("makespan"),
                score=sol.get("score"),
                config_json={
                    "regola_usata": sol.get("regola"),
                    "penalità_totale": sol.get("penalità"),
                    "parametri_run": sol_config,
                    "solver_metadata": {k: v for k, v in sol.items() if k not in ['soluzione', 'schedule']}
                }
            )
            self.schedule_repo.create(new_schedule)

            # 6. Salvataggio ScheduleActivity
            # L'orchestrator può ritornare lo schedule come lista di dict o come dict id->start
            raw_sol = sol.get("soluzione") or sol.get("schedule")
            
            # Normalizziamo lo schedule in un dizionario {id: {start, end, duration}}
            schedule_details = {}
            if isinstance(raw_sol, list):
                for item in raw_sol:
                    act_id = item.get("activity")
                    schedule_details[act_id] = {
                        "start": item.get("start"),
                        "end": item.get("end"),
                        "duration": item.get("end") - item.get("start")
                    }
            elif isinstance(raw_sol, dict):
                # Se è un dict, le durate sono spesso in un campo separato
                durations = sol.get("durations") or sol_config.get("durations", {})
                for act_id_str, start in raw_sol.items():
                    act_id = int(act_id_str)
                    dur = durations[act_id] if isinstance(durations, list) else durations.get(act_id_str, 0)
                    schedule_details[act_id] = {
                        "start": start,
                        "end": start + dur,
                        "duration": dur
                    }

            # Salvataggio effettivo
            for act_id, times in schedule_details.items():
                if act_id in activity_map:
                    activity = activity_map[act_id]
                    
                    # Estraiamo info aggiuntive dalla config (fondamentale per RCPSP/MAX)
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
                        start_time=times["start"],
                        end_time=times["end"],
                        duration=times["duration"],
                        # Il consumo di risorse è fisso per l'attività nel progetto (master data)
                        # ma lo salviamo qui per facilitare la visualizzazione del Gantt "caricato"
                        resource_usage=activity.activity_config_json.get("resource_requirements", {}),
                        release_date=release_date,
                        deadline=deadline
                    )
                    self.sa_repo.create(sa)

        return experiment
